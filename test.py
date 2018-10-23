# Author:Jesi
# Time : 2018/8/18 18:18
def f(x,l=[]):
    for i in range(x):
        l.append(i)
    print (l)

f(2)
f(3,[3,2,1])
f(3)