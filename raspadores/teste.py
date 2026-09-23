desconto = "-"
preco = 20
preco_original = 30

calculo = (1 - (preco / preco_original)) * 100
desconto = f"{round(calculo, 2)}%"

print("\ndesconto: ", desconto)
