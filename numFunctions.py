def product(x, y):
    return x * y

def get_number(start, end):
    err_msg = "Please enter only numbers between %d and %d!" % (start, end)
    while True:
        try:
            number = int(input("Enter number between %d and %d: " % (start, end)))
        except ValueError:
            print(err_msg)
            continue
        if  number < start or number > end:
            print(err_msg)
            continue
        else:           
            break
    return number

def score2grade():
    print("Enter score below to return grade")
    score = get_number(1, 100)
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"
    return grade

def is_leap(year):
    if (year % 4 == 0) and ((year % 100 != 0) or (year % 100 == 0 and year % 400 == 0)):
        return year
    else:
        False

def calculate_change():
    err_msg = "Enter ammount below to calculate coins"
    coins = {1: "penny", 5: "nickel", 10: "dime", 25: "quarter"}
    amount = get_number(1, 99)
    change_dict = {}
    for value in sorted(coins, reverse=True):
        change_dict[coins[value]] = divmod(amount, value)[0]
        amount = divmod(amount, value)[1]
    return change_dict

def type_err():
    print(

def calc_app():
    oper_err = "Use only '+', '-', '*', '/', '%' or '**' for OP"
    type_err = "Use only integers/floats for N1 and N2"
    while True:
        calc = input("Enter 2 numbers and an operand (N1 OP N2): ")
        if len(calc.split()) != 3:
            continue
        try:
            n1 = float(calc.split()[0])
            n2 = float(calc.split()[2])
        except ValueError:
            print(type_err)
            continue
        op = str(calc.split()[1])
        if op == "+":
            result = n1 + n2
            break
        elif op == "-":
            result = n1 - n2
            break
        elif op == "*":
            result = n1 * n2
            break
        elif op == "/":
            result = n1 / n2
            break
        elif op == "%":
            result = n1 % n2
            break
        elif op == "**":
            result = n1 ** n2
            break
        else:
            print(oper_err)
            continue
    if str(result).split(".")[1] == "0":
        result = int(result)
    return result

def sales_tax():
    err_msg = "Enter only numbers"
    vat = 16
    cas = 11
    unemploy = 10.5
    while True:
        amount = input("Enter monatary amount in RON: ")
        try:
            amount = float(amount)
            break
        except ValueError:
            print(err_msg)
            continue
    vat_amount = amount * vat / 100
    cas_amount = amount * cas / 100
    unemploy_amount = amount * unemploy / 100
    total_tax_amount = amount + vat_amount + cas_amount + unemploy_amount
    total_fmt = "%.2f RON" % total_tax_amount
    return total_fmt
