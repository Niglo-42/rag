with open("new.txt", "w") as file:
    content = ""
    for i in range(1992):
        content += "a"
    content += "\n"
    for i in range(1800):
        content += "a"
    content += "\n"
    for i in range(118):
        content += "a"
    file.write(content)