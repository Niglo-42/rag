import fire

class RagCLI:
    pass

if __name__ == "__main__":
    # Launch CLI
    try:
        fire.Fire(RagCLI)
    except (EOFError, KeyboardInterrupt):
        print('problema')
    print("hello")