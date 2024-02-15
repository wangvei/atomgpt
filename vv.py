#conda activate chemnlp

from dataclasses import dataclass
from dataclasses import dataclass, field
from typing import Optional, Dict, Sequence
from tqdm import tqdm
import transformers
import torch
from transformers import (
    GPT2Tokenizer,
    GPT2LMHeadModel,
    GPT2Config,
    Trainer,
    TrainingArguments,
)
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import numpy as np
import os
from jarvis.core.atoms import Atoms
os.environ["WANDB_ANONYMOUS"] = "must"
import glob
import torch
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
from jarvis.core.atoms import Atoms
from tqdm import tqdm
import transformers
import time
np.random.seed(42)
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
os.environ["PYTHONHASHSEED"] = str(42)
os.environ["CUBLAS_WORKSPACE_CONFIG"] = str(":4096:8")
torch.use_deterministic_algorithms(True)

IGNORE_INDEX = -100
device = "cpu"
if torch.cuda.is_available():
    device = torch.device("cuda")
def get_crystal_string(atoms):
    # structure = Structure.from_str(cif_str, fmt="cif")
    # jatoms=pmg_to_atoms(structure)
    # jatoms=Atoms.from_cif(from_string=cif_str)
    # print(jatoms,jatoms.lattice.abc,jatoms.lattice.angles)
    # Randomly translate within the unit cell

    lengths = atoms.lattice.abc  # structure.lattice.parameters[:3]
    angles = atoms.lattice.angles
    atom_ids = atoms.elements
    frac_coords = atoms.frac_coords

    crystal_str = (
        " ".join(["{0:.1f}".format(x) for x in lengths])
        + "\n"
        + " ".join([str(int(x)) for x in angles])
        + "\n"
        + "\n".join(
            [
                str(t) + "\n" + " ".join(["{0:.2f}".format(x) for x in c])
                for t, c in zip(atom_ids, frac_coords)
            ]
        )
    )

    return crystal_str

# Define a custom dataset class for regression
class AtomGPTDataset(Dataset):
    def __init__(self, texts=[], targets=[], ids=[],tokenizer='', max_length=128):
        self.texts = texts
        self.targets = targets
        self.tokenizer = tokenizer
        self.max_length = max_length
        if not ids:
           ids=['text-'+str(i) for i in range(len(texts))]
        self.ids = ids
    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        inputs = self.tokenizer(
            self.texts[idx],
            return_tensors="pt",
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
        )
        return inputs, self.ids[idx], torch.tensor(self.targets[idx], dtype=torch.float32)


# Example usage
if __name__ == "__main__":

    # Load pre-trained tokenizer
    # tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    # model = GPT2LMHeadModel.from_pretrained("gpt2")

    from jarvis.db.figshare import data
    import json,zipfile
    dft_3d = data("dft_3d")
    bench = json.loads(zipfile.ZipFile("/wrk/knc6/AFFBench/jarvis_leaderboard/jarvis_leaderboard/benchmarks/AI/SinglePropertyPrediction/dft_3d_exfoliation_energy.json.zip").read("dft_3d_exfoliation_energy.json"))
    train_atoms=[]
    val_atoms=[]
    test_atoms=[]
    train_targets=[]
    val_targets=[]
    test_targets=[]
    train_ids=list(bench['train'].keys())
    val_ids=list(bench['val'].keys())
    test_ids=list(bench['test'].keys())

    model_name = "mistralai/Mistral-7B-Instruct-v0.1"
    model_name = "gpt2"
    model = transformers.AutoModelForCausalLM.from_pretrained(model_name)

    tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)

    batch_size = 16
    max_length = 128
    num_epochs = 100
    learning_rate = 5e-5
    criterion = torch.nn.L1Loss()
    # Define example regression data (texts and corresponding numeric targets)
    train_texts=[]
    train_targets=[]
    train_ids_temp=[]
    val_texts=[]
    val_targets=[]
    val_ids_temp=[]
    test_texts=[]
    test_targets=[]
    test_ids_temp=[]

    for i in dft_3d:
       if i['exfoliation_energy']!='na':
          atoms=Atoms.from_dict(i['atoms'])
          tmp=get_crystal_string(atoms)
          if i['jid'] in train_ids:
           train_texts.append(tmp)
           train_targets.append(i['exfoliation_energy'])
           train_ids_temp.append(i['jid'])
          elif i['jid'] in val_ids:
           val_texts.append(tmp)
           val_targets.append(i['exfoliation_energy'])
           val_ids_temp.append(i['jid'])
          elif i['jid'] in test_ids:
           test_texts.append(tmp)
           test_targets.append(i['exfoliation_energy'])
           test_ids_temp.append(i['jid'])
        
    ###Fast test###    
    train_texts = [
        "This is the first example text.",
        "Second example is a bit longer than the first one, but still within the max length.",
        "Third example is the longest among these three examples. It exceeds the max length and will be truncated.",
        "Second example is a bit longer than the first one, but still within the max length.",
    ]
    train_targets = [10.2, 15.5, 20.1, 15.5]  # Example regression targets
    val_texts = test_texts = train_texts
    val_targets = test_targets = train_targets
    train_ids_temp=['a','b','c','d']
    val_ids_temp = test_ids_temp = train_ids_temp
    batch_size = 2
    num_epochs = 3
    ##############################
    # Fine-tune the last layer of GPT-2 for regression
    # fine_tune_gpt2_regression(train_texts, train_targets, tokenizer)
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({"pad_token": "[PAD]"})
        model.resize_token_embeddings(len(tokenizer))
    model.lm_head = torch.nn.Linear(
        model.config.hidden_size, 1
    )  # Single output for regression
    model.to(device)
    optimizer = transformers.AdamW(
        model.parameters(),
        lr = learning_rate
    )
    #train_texts.to(device)
    #train_targets.to(device)
    #test_texts.to(device)
    #test_targets.to(device)
    # Prepare datasets and dataloaders with data collator
    train_dataset = AtomGPTDataset(
        texts=train_texts, targets=train_targets, ids=train_ids_temp, tokenizer=tokenizer, max_length=max_length
    )
    val_dataset = AtomGPTDataset(
        texts=val_texts, targets=val_targets, tokenizer=tokenizer, ids=val_ids_temp, max_length=max_length
    )
    test_dataset = AtomGPTDataset(
        texts=test_texts, targets=test_targets, tokenizer=tokenizer, ids=test_ids_temp, max_length=max_length
    )
    
    #val_dataset = train_dataset
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size)
    val_dataloader = DataLoader(val_dataset, batch_size=batch_size)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size)
    steps_per_epoch = len(train_dataloader)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=learning_rate,
        epochs=num_epochs,
        steps_per_epoch=steps_per_epoch,
        # pct_start=pct_start,
        pct_start=0.3,
    )
    print('train_data',len(train_texts))
    print('test_data',len(test_texts))
    output_dir = "out"
    best_loss = np.inf
    for epoch in range(num_epochs):
        model.train()
        t1=time.time()
        for batch in train_dataloader:
            train_loss = 0
            train_result = []
            input_ids = batch[0]["input_ids"].squeeze() #.squeeze(0)
            predictions = model(input_ids.to(device)).logits.squeeze().mean(dim=-1)
            targets = batch[2].squeeze()
            loss = criterion(predictions.squeeze(), targets.squeeze().to(device))
            #print('train',predictions,targets)
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            train_loss += loss.item()
        train_loss = train_loss/len(train_dataloader)
        t2=time.time()
        train_time=round(t2-t1,3)
        model.eval()

        total_eval_mae_loss = 0
        predictions_list = []
        targets_list = []
        val_loss = 0
        t1=time.time()
        for batch in val_dataloader:
          with torch.no_grad():
            input_ids = batch[0]["input_ids"].squeeze(0) #.squeeze(0)
            predictions = model(input_ids.to(device)).logits.squeeze().mean(dim=-1)
            targets = batch[2].squeeze()
            #print('val',predictions,targets)
            loss = criterion(predictions.squeeze(), targets.squeeze().to(device))
            val_loss += loss.item()
        if val_loss < best_loss:
                best_loss = val_loss
                best_model_name = "best_model.pt"
                torch.save(
                    model.state_dict(),
                    os.path.join(output_dir, best_model_name),
                )
        val_loss = val_loss/len(val_dataloader)
        t2=time.time()
        val_time=round(t2-t1,3)
        #print("Epoch, train loss, val loss, train_time, val_time",epoch,train_loss,val_loss,train_time,val_time)
        formatted_output = f"Epoch {epoch}, train_loss {train_loss:.4f}, val_loss {val_loss:.4f}, train_time {train_time:.2f}, val_time {val_time:.2f}"
        print(formatted_output)
    f=open('test_results.csv','w')
    f.write('id,target,predictions\n')
    for batch in test_dataloader:
      with torch.no_grad():
        input_ids = batch[0]["input_ids"].squeeze(0) #.squeeze(0)
        predictions = model(input_ids.to(device)).logits.squeeze().mean(dim=-1)
        ids=batch[1]
        targets = batch[2].squeeze()
      
        for ii,jj,kk in zip(targets,predictions,ids):
             #print(kk,ii.cpu().detach().numpy().tolist(),jj.cpu().detach().numpy().tolist())
             f.write("%s, %6f, %6f\n" % (kk, ii.cpu().detach().numpy().tolist(), jj.cpu().detach().numpy().tolist()))
    f.close()
