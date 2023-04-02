money = 50000000000000000000000000
name = input("请输入您的姓名：")


def check(t):
    if t:
        print("----------查询-------------")

    print(f"尊敬的{name}，您的银行卡余额为{money}")


def qu():
    print("----------取款-------------")
    x = int(input("请输入取款金额："))
    global money
    money -= x
    check(0)


def save():
    print("-----------存款------------")
    y = int(input("请输入存款金额："))
    global money
    money += y
    check(0)


def end():
    print("操作结束，祝您生活愉快！")


def main():
    print("------------主菜单-----------")
    print(f"您好，尊敬的{name}，欢迎来到小王龙银行！")
    print("查询余额\t\t请按数字“1”")
    print("存入余额\t\t请按数字“2”")
    print("取出余额\t\t请按数字“3”")
    print("结束操作\t\t请按数字“4”")
    return int(input("请输入指令:"))


while 1:
    key_number = main()
    if key_number == 1:
        check(1)
        continue
    elif key_number == 2:
        save()
        continue
    elif key_number == 3:
        qu()
        continue
    elif key_number == 4:
        end()
        break
    else:
        end()
        break

