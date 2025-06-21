from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from .models import ContaBancaria, Lancamento
from .services import recalcular_saldo_conta

class ContaBancariaServiceTest(TestCase):

    def setUp(self):
        """
        Configura o ambiente de teste criando um usuário e uma conta bancária.
        Este método é executado antes de cada teste.
        """
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.conta = ContaBancaria.objects.create(
            usuario=self.user,
            nome_banco='Banco Teste',
            numero_conta='12345-6',
            saldo_inicial=Decimal('1000.00'),
            data_saldo_inicial=date(2023, 1, 1)
        )

    def test_recalcular_saldo_conta_service(self):
        """
        Testa diretamente o serviço recalcular_saldo_conta.
        """
        # Cria alguns lançamentos
        Lancamento.objects.create(
            usuario=self.user,
            conta_bancaria=self.conta,
            descricao='Salário',
            valor=Decimal('3000.00'),
            tipo='C', # Crédito
            data_competencia=date(2023, 1, 5),
            data_caixa=date(2023, 1, 5)
        )
        Lancamento.objects.create(
            usuario=self.user,
            conta_bancaria=self.conta,
            descricao='Aluguel',
            valor=Decimal('1200.00'),
            tipo='D', # Débito
            data_competencia=date(2023, 1, 10),
            data_caixa=date(2023, 1, 10)
        )
        Lancamento.objects.create(
            usuario=self.user,
            conta_bancaria=self.conta,
            descricao='Supermercado',
            valor=Decimal('450.50'),
            tipo='D', # Débito
            data_competencia=date(2023, 1, 15),
            data_caixa=date(2023, 1, 15)
        )

        # Chama o serviço para recalcular o saldo
        recalcular_saldo_conta(self.conta)

        # Atualiza a instância da conta do banco de dados
        self.conta.refresh_from_db()

        # Saldo esperado = 1000 (inicial) + 3000 (crédito) - 1200 (débito) - 450.50 (débito) = 2349.50
        saldo_esperado = Decimal('2349.50')
        self.assertEqual(self.conta.saldo_calculado, saldo_esperado)

    def test_sinal_post_save_lancamento_criacao(self):
        """
        Testa se o saldo da conta é atualizado via sinal ao criar um novo lançamento.
        """
        Lancamento.objects.create(
            usuario=self.user,
            conta_bancaria=self.conta,
            descricao='Crédito Teste',
            valor=Decimal('500.00'),
            tipo='C',
            data_competencia=date(2023, 2, 1),
            data_caixa=date(2023, 2, 1)
        )
        self.conta.refresh_from_db()
        # Saldo esperado = 1000 (inicial) + 500 (crédito) = 1500.00
        self.assertEqual(self.conta.saldo_calculado, Decimal('1500.00'))

    def test_sinal_post_delete_lancamento(self):
        """
        Testa se o saldo da conta é atualizado via sinal ao deletar um lançamento.
        """
        lancamento = Lancamento.objects.create(
            usuario=self.user,
            conta_bancaria=self.conta,
            descricao='Débito a ser deletado',
            valor=Decimal('200.00'),
            tipo='D',
            data_competencia=date(2023, 3, 1),
            data_caixa=date(2023, 3, 1)
        )
        self.conta.refresh_from_db()
        # Saldo após criação = 1000 - 200 = 800
        self.assertEqual(self.conta.saldo_calculado, Decimal('800.00'))

        # Deleta o lançamento
        lancamento.delete()
        self.conta.refresh_from_db()
        # Saldo após deleção deve voltar ao inicial = 1000
        self.assertEqual(self.conta.saldo_calculado, Decimal('1000.00'))

    def test_sinal_post_save_conta_bancaria(self):
        """
        Testa se o saldo é recalculado ao alterar o saldo inicial da conta.
        """
        Lancamento.objects.create(
            usuario=self.user,
            conta_bancaria=self.conta,
            descricao='Débito fixo',
            valor=Decimal('300.00'),
            tipo='D',
            data_competencia=date(2023, 5, 1),
            data_caixa=date(2023, 5, 1)
        )
        self.conta.refresh_from_db()
        # Saldo com saldo inicial de 1000 = 1000 - 300 = 700
        self.assertEqual(self.conta.saldo_calculado, Decimal('700.00'))

        # Altera o saldo inicial da conta
        self.conta.saldo_inicial = Decimal('2000.00')
        self.conta.save()
        self.conta.refresh_from_db()
        # Saldo com novo saldo inicial = 2000 - 300 = 1700
        self.assertEqual(self.conta.saldo_calculado, Decimal('1700.00'))
