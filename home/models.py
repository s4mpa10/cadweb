import locale
from django.db import models
import hashlib
from decimal import Decimal, ROUND_HALF_UP
# from .forms import *

# Modelo de validação de campos

# class MeuFormulario(forms.Form):
#     nome_completo = forms.CharField(validators=[validar_nome()])

class Categoria(models.Model): 
    nome = models.CharField(max_length = 100)
    ordem = models.IntegerField()

    def __str__(self):
        return self.nome
    
class Cliente(models.Model):
    nome = models.CharField(max_length=100) 
    cpf = models.CharField(max_length=15,verbose_name="C.P.F")
    datanasc = models.DateField(verbose_name="Data de Nascimento")

    def __str__(self):
        return self.nome
    
    @property
    def datanascimento(self):
          """Retorna a data de nascimento no formato DD/MM/AAAA """
          if self.datanasc:
               return self.datanasc.strftime('%d/%m/%Y')
          return None

class Produto(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2, blank=False)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    img_base64 = models.TextField(blank=True)

    def __str__(self):
        return self.nome
    
    @property
    def estoque(self):
        estoque_item, flag_created = Estoque.objects.get_or_create(produto=self, defaults={'qtde': 0})
        return estoque_item
    
class Estoque(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)  
    qtde = models.IntegerField()

    def __str__(self):
        return f'{self.produto.nome} - Quantidade: {self.qtde}'


class Pedido(models.Model):

    NOVO = 1
    EM_ANDAMENTO = 2
    CONCLUIDO = 3
    CANCELADO = 4

    STATUS_CHOICES = [
        (NOVO, 'Novo'),
        (EM_ANDAMENTO, 'Em Andamento'),
        (CONCLUIDO, 'Concluído'),
        (CANCELADO, 'Cancelado'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    produtos = models.ManyToManyField(Produto, through='ItemPedido')
    data_pedido = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=NOVO)

    def __str__(self):
            return f"Pedido {self.id} - Cliente: {self.cliente.nome} - Status: {self.get_status_display()}"
    
    @property
    def data_pedidof(self):
        if self.data_pedido:
            return self.data_pedido.strftime('%d/%m/%Y %H:%M')
        return None

    @property 
    def total(self):
        total = sum(item.qtde * item.preco for item in self.itens.all())
        return total
    
    @property
    def qtdeItens(self):
        return self.itempedido_set.count()
    
    @property
    def pagamentos(self):
        return Pagamento.objects.filter(pedido=self)

    @property
    def total_pago(self):
        total = sum(pagamento.valor for pagamento in self.pagamentos.all())
        return total
    
    @property
    def debito(self):
        valor_debito = self.total - self.total_pago 
        return valor_debito
    
    @property
    def data_pedido_key(self):
        if self.data_pedido:
            return self.data_pedido.strftime('%Y%m%d')
        return None
    
    @property
    def chave_acesso(self):
        # Combina o ID do pedido e a data formatada
        if self.id and self.data_pedido_key:
            dados_comb = f"{self.id}-{self.data_pedido_key}"
        
            # Cria o hash com sha256
            sha256 = hashlib.sha256()
            sha256.update(dados_comb.encode('utf-8'))  # Codificando a string para bytes
            key_final = f"{self.data_pedido_key}{self.id}{sha256.hexdigest()}"
            return key_final  # Retorna o hash gerado
        return None
    
    @property
    def calculoICMS(self):
        icms = Decimal('0.18')
        calculo = (self.total * icms).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return calculo
    
    @property
    def calculoIPI(self):
        ipi = Decimal('0.05')
        calculo = (self.total * ipi).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return calculo
    
    @property
    def calculoPIS(self):
        pis = Decimal('0.0165')
        calculo = (self.total * pis).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return calculo

    @property
    def calculoCONFINS(self):
        confins = Decimal('0.076')
        calculo = (self.total * confins).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return calculo
    
    @property
    def total_impostos(self):
        soma_impostos = (self.calculoICMS + self.calculoIPI + self.calculoPIS + self.calculoCONFINS).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return soma_impostos
    
    @property
    def valor_final(self):
        valor = (self.total + self.total_impostos).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return valor


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")    
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)  
    qtde = models.PositiveIntegerField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.produto.nome} (Qtde: {self.qtde}) - Preço Unitário: {self.preco}"
    
    @property
    def calculoTotal(self):
        total = self.qtde * self.produto.preco
        return total

    @property
    def total(self):
        total = sum(item.qtde * item.preco for item in self.itempedido_set.all())
        return total


class Pagamento(models.Model):
    DINHEIRO = 1
    CREDITO = 2
    DEBITO = 3
    PIX = 4
    TICKET = 5
    OUTRA = 6

    FORMA_CHOICES = [
        (DINHEIRO, 'Dinheiro'),
        (CREDITO, 'Credito'),
        (DEBITO, 'Debito'),
        (PIX, 'Pix'),
        (TICKET, 'Ticket'),
        (OUTRA, 'Outra'),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE) 
    forma = models.IntegerField(choices=FORMA_CHOICES)
    valor = models.DecimalField(max_digits = 10, decimal_places=2, blank = False )
    data_pgto = models.DateTimeField(auto_now_add=True)

    @property
    def data_pgtof(self):
        """Retorna a data formatada: DD/MM/AAAA HH:MM"""
        if self.data_pgto:
            return self.data_pgto.strftime('%d/%m/%Y %H:%M')
        return None