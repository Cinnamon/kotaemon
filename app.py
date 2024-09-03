import os
from ktem.main import App
from theflow.settings import settings as flowsettings
from kotaemon.llms import EndpointChatLLM

# Load all settings from flowsettings
for setting in dir(flowsettings):
    if setting.isupper():
        globals()[setting] = getattr(flowsettings, setting)

class CustomApp(App):
    def __init__(self):
        super().__init__()
        self.setup_llm()

    def setup_llm(self):
        llm_config = KH_LLMS.get('ollama', {}).get('spec', {})
        if llm_config.get('__type__') == 'kotaemon.llms.EndpointChatLLM':
            self.llm = EndpointChatLLM(**llm_config)
            print(f"LLM initialized: {type(self.llm).__name__}")
        else:
            print("Warning: Expected LLM configuration not found")

# Initialize the custom app
app = CustomApp()

# Check which LLM is being used
if hasattr(app, 'llm'):
    print(f"App is using LLM: {type(app.llm).__name__}")
else:
    print("App does not have an 'llm' attribute")

demo = app.make()
demo.queue().launch(
    favicon_path=app._favicon,
    inbrowser=True,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        KH_APP_DATA_DIR,
    ],
)
