print([1,24,52,1,41][:-1])

print([1,3,4,5].index(4))

print([1,15,161][-0])

print(len(([x for x in ["27313","1419"] if x[0] == "3"]+[""])[0]))

l = [17,17]+[15,1]
print([x for i, x in enumerate(l) if x in l[:i]][0])
