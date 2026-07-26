"""
Lesson 2 - "Hello, Model": confirm Foundry Local works from Python.

This script loads a tiny local LLM through the Foundry Local SDK and asks it
one question, streaming the answer token by token. Everything runs on your
machine - no internet needed after the model is downloaded once.

Run it with:   python hello_model.py
"""

from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    # 1. Start the Foundry Local manager (talks to the local service).
    config = Configuration(app_name="rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    # 2. Make sure the hardware execution providers are downloaded/registered.
    #    (First run may download some acceleration packages - that's normal.)
    manager.download_and_register_eps()

    # 3. Pick a small, fast chat model from the catalog by its alias.
    #    Foundry Local automatically chooses the best build for your hardware.
    model = manager.catalog.get_model("qwen2.5-0.5b")

    # 4. Download it (skips if already cached) and load it into memory.
    model.download(lambda p: print(f"\rDownloading model: {p:.0f}%", end="", flush=True))
    print()
    model.load()
    print("Model loaded. Asking a question...\n")

    # 5. Get a chat client and send one message.
    client = model.get_chat_client()
    messages = [{"role": "user", "content": "In one sentence, what is a large language model?"}]

    print("Assistant: ", end="", flush=True)
    for chunk in client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
    print("\n")

    # 6. Free the memory.
    model.unload()
    print("Done. Foundry Local is working correctly.")


if __name__ == "__main__":
    main()
