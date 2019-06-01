import sys


def main():
    filename = sys.argv[1]
    replace_couples = sys.argv[2:]
    assert len(replace_couples) % 2 == 0

    with open(filename, "r") as fp:
        x = fp.read()

    for i in range(len(replace_couples) // 2):
        a, b = replace_couples[i*2:(i+1)*2]
        x = x.replace(a, b)

    with open(filename, "w") as fp:
        fp.write(x)


if __name__ == "__main__":
    main()
