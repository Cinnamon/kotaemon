import os
from ktem.main import App
from theflow.settings import settings as flowsettings
from kotaemon.llms import EndpointChatLLM
from kotaemon.embeddings import OpenAIEmbeddings, FastEmbedEmbeddings

# Load all settings from flowsettings
for setting in dir(flowsettings):
    if setting.isupper():
        globals()[setting] = getattr(flowsettings, setting)

class CustomApp(App):
    def __init__(self):
        super().__init__()
        self.setup_llm()
        self.setup_embeddings()

    def setup_llm(self):
        llm_config = KH_LLMS.get('ollama', {}).get('spec', {})
        llm_type = llm_config.get('__type__')
        if llm_type:
            LLMClass = self.get_class_from_type(llm_type)
            self.llm = LLMClass(**llm_config)
            print(f"LLM initialized: {type(self.llm).__name__}")
        else:
            print("Warning: LLM configuration not found")

    def setup_embeddings(self):
        self.embeddings = {}
        for name, config in KH_EMBEDDINGS.items():
            embedding_type = config['spec'].get('__type__')
            if embedding_type:
                EmbeddingClass = self.get_class_from_type(embedding_type)
                self.embeddings[name] = EmbeddingClass(**config['spec'])
                print(f"Embedding {name} initialized: {embedding_type}")
            else:
                print(f"Warning: Embedding configuration for {name} not found")

    @staticmethod
    def get_class_from_type(class_type):
        module_name, class_name = class_type.rsplit('.', 1)
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

# Initialize the custom app
app = CustomApp()

# Check which LLM and embeddings are being used
if hasattr(app, 'llm'):
    print(f"App is using LLM: {type(app.llm).__name__}")
else:
    print("App does not have an 'llm' attribute")

if hasattr(app, 'embeddings'):
    for name, embedding in app.embeddings.items():
        print(f"App is using Embedding {name}: {type(embedding).__name__}")
else:
    print("App does not have an 'embeddings' attribute")

demo = app.make()
demo.queue().launch(
    favicon_path=app._favicon,
    inbrowser=True,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        KH_APP_DATA_DIR,
    ],
)
