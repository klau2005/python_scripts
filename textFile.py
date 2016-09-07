#!/usr/bin/env python3

'textFile.py -- create/display text files'

import sys,os
from os import linesep as ls
from shutil import get_terminal_size as term_size

# calculate number of # to fill term width
prg_dialogue = "Enter file name (back to return to main screen): "
nb_hash = term_size()[0]
hash_line = "#" * nb_hash

# function to create file
def write_file():
    while True:
        fname = input(prg_dialogue).strip()
        create_file = True
        if fname == "back":
            print("Going back to main program")
            create_file = False
            break
        elif os.path.exists(fname):
            print("ERROR: %s already exists" % fname)
        else:
            break

    if create_file:
        # get file content (text) lines
        all = []
        print("%sEnter lines ('.' by itself to quit).%s" % (ls, ls))

        # loop until user terminates input
        while True:
            entry = input("> ")
            if entry == '.':
                break
            else:
                all.append(entry)

        # write lines to file with proper line-ending
        with open(fname, "w") as fobj:
            fobj.write(ls.join(all))
            fobj.write(ls)
            print("DONE!")

# function to display file
def read_file():
    #get filename
    while True:
        fname = input(prg_dialogue).strip()
        if fname == "back":
            print("Going back to main program")
            break
        elif not os.path.exists(fname):
            print("ERROR: %s doesn't exist" % fname)
            continue
        else:
            #display contents to the screen
            with open(fname, "r") as fobj:
                print(hash_line)
                for each_line in fobj:
                    print(each_line.strip(ls))
                print(hash_line)
                break

# function to edit file
def edit_file():
    #get filename
    while True:
        fname = input(prg_dialogue).strip()
        if fname == "back":
            print("Going back to main program")
            break
        elif not os.path.exists(fname):
            print("ERROR: %s doesn't exist" % fname)
            continue
        else:
            #create list to store file contents
            file_list = []
            with open(fname, "r") as fobj:
                for each_line in fobj:
                    file_list.append(each_line)
            new_file_list = []
            print("Enter edited line ('.' to leave intact)")
            for item in file_list:
                print(item.strip("\n"))
                edited_line = input("> ")
                if edited_line == ".":
                    new_file_list.append(item)
                else:
                    new_file_list.append(edited_line + "\n")
            edit = input("Do you want to save changes to the file? Y/N (default No): ")
            if edit in ("Y", "y"):
                with open(fname, "w") as fobj:
                    for item in new_file_list:
                        fobj.write(item)
                print("File %s has been modified" % fname)
            else:
                print("File %s left unchanged" % fname)

# define main function
def main():
    while True:
        action = input("Enter read/create/edit as operating mode (exit to quit): ")
        if action == "read":
            read_file()
            continue
        elif action == "create":
            write_file()
            continue
        elif action == "edit":
            edit_file()
            continue
        elif action == "exit":
            print("Program exit!")
            sys.exit(0)
        else:
            print("Unrecognized command: %s" % action)
        continue

if __name__ == '__main__':
    main()

