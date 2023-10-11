'''
# Sample code to perform I/O:

name = input()                  # Reading input from STDIN
print('Hi, %s.' % name)         # Writing output to STDOUT

# Warning: Printing unwanted or ill-formatted data to output will cause the test cases to fail
'''

# Write your code here
T = input()
cost = []
cost_green = []
cost_purple = []
N = []
value = []

for i in range(int(T)):
    a,b = input().split()
    cost_green.append(int(a))
    cost_purple.append(int(b))
    N.append(int(input()))
    for j in range(N[i]):
        a,b = input().split()
        value.append(int(a))
        value.append(int(b))

for i in range(int(T)):
    index = i * N[i]
    cost.append(0)
    cost_t = []
    cost_t.append(0)
    cost_t.append(0)
    for j in range(0, 2 * N[i], 2):
        if value[index+j]*value[index+j+1] == 1:
            print('yes')
            cost[i] += (cost_green[i]+cost_purple[i])
        elif value[index+j] == 1:
            cost_t[0] += 1
        elif value[index+j+1] == 1:
            cost_t[1] += 1
    print(min(cost_t),max(cost_green[i],cost_purple[i]),max(cost_t),min(cost_green[i],cost_purple[i]))
    print(cost_t)
    cost[i] += (min(cost_t)*max(cost_green[i],cost_purple[i]) + max(cost_t)*min(cost_green[i],cost_purple[i]))

for i in (cost):
    print(i)