from ktem.main import App

app = App()
demo = app.make()
demo.queue().launch(favicon_path=app._favicon)
