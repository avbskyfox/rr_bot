from rr_telebot.dispatcher import run


def main():
    while True:
        try:
            run()
        except:
            pass


if __name__ == '__main__':
    main()
