import os
from pathlib import Path
import re
from ktem.main import App
from theflow.settings import settings as flowsettings
from unsloth import FastLanguageModel
import torch

# Load all settings from flowsettings
for setting in dir(flowsettings):
    if setting.isupper():
        globals()[setting] = getattr(flowsettings, setting)

def get_loss_from_snapshot(snapshot_path):
    try:
        # Load the optimizer state
        optimizer_state = torch.load(os.path.join(snapshot_path, "optimizer.pt"))
        # Extract the loss from the state
        loss = optimizer_state.get('state', {}).get(0, {}).get('loss_scale', float('inf'))
        return loss
    except Exception as e:
        print(f"Error reading loss from {snapshot_path}: {e}")
        return float('inf')

def find_best_snapshot(base_dir, max_snapshots=100):
    snapshots = sorted(Path(base_dir).glob("checkpoint-*"), key=os.path.getmtime, reverse=True)
    best_snapshot = None
    lowest_loss = float('inf')

    for snapshot in snapshots[:max_snapshots]:
        loss = get_loss_from_snapshot(snapshot)
        if loss < lowest_loss:
            lowest_loss = loss
            best_snapshot = snapshot

    return best_snapshot, lowest_loss

class CustomApp(App):
    def __init__(self):
        super().__init__()
        self.setup_llm()

    def setup_llm(self):
        base_dir = "/content/drive/MyDrive/nouget_sk_alpaca_instruct/"
        best_snapshot, lowest_loss = find_best_snapshot(base_dir)
        
        if best_snapshot:
            print(f"Best snapshot: {best_snapshot}, Loss: {lowest_loss}")
            max_seq_length = 2048
            dtype = None
            load_in_4bit = True

            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name = str(best_snapshot),
                max_seq_length = max_seq_length,
                dtype = dtype,
                load_in_4bit = load_in_4bit,
            )
            FastLanguageModel.for_inference(model)
            
            self.model = model
            self.tokenizer = tokenizer
            print(f"Model loaded from snapshot: {best_snapshot}")
        else:
            print("No valid snapshot found")

# Initialize the custom app
app = CustomApp()

# Check if the model is loaded
if hasattr(app, 'model') and hasattr(app, 'tokenizer'):
    print(f"App has loaded the model and tokenizer")
else:
    print("App failed to load the model and tokenizer")

demo = app.make()
demo.queue().launch(
    favicon_path=app._favicon,
    inbrowser=True,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        KH_APP_DATA_DIR,
    ],
)
