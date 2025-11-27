class a:
	b = 1


x = a()
print(x.b)
x.b = 2
print(x.b, a.b)

y = a
print(y.b)
