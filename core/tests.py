from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from .models import ContaBancaria, Lancamento, Categoria
from .services import recalcular_saldo_conta, gerar_dados_grafico_saldo, gerar_dados_grafico_categorias

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

class DashboardServiceTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        Configura dados que serão usados por todos os testes da classe.
        Usar setUpTestData é mais eficiente para dados que não mudam entre os testes.
        """
        cls.user = User.objects.create_user(username='dashboarduser', password='password123')
        
        # Contas Bancárias
        cls.conta1 = ContaBancaria.objects.create(
            usuario=cls.user, nome_banco='Banco A', numero_conta='111',
            saldo_inicial=Decimal('1000.00'), data_saldo_inicial=date(2023, 1, 1)
        )
        cls.conta2 = ContaBancaria.objects.create(
            usuario=cls.user, nome_banco='Banco B', numero_conta='222',
            saldo_inicial=Decimal('500.00'), data_saldo_inicial=date(2023, 2, 1)
        )

        # Categorias
        cls.cat_moradia = Categoria.objects.create(nome='Moradia', usuario=cls.user)
        cls.cat_alimentacao = Categoria.objects.create(nome='Alimentação', usuario=cls.user)
        cls.cat_transporte = Categoria.objects.create(nome='Transporte', usuario=cls.user)
        cls.cat_lazer = Categoria.objects.create(nome='Lazer', usuario=cls.user)
        cls.cat_saude = Categoria.objects.create(nome='Saúde', usuario=cls.user)
        cls.cat_educacao = Categoria.objects.create(nome='Educação', usuario=cls.user)
        cls.cat_salario = Categoria.objects.create(nome='Salário', usuario=cls.user)

        # --- Lançamentos para teste de saldo (Mês de Março/2023) ---
        # Anteriores a Março
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='C', valor=Decimal('2000'), data_caixa=date(2023, 1, 15), data_competencia=date(2023, 1, 15), descricao='Salario Jan')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('800'), data_caixa=date(2023, 1, 20), data_competencia=date(2023, 1, 20), descricao='Aluguel Jan')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='C', valor=Decimal('2000'), data_caixa=date(2023, 2, 15), data_competencia=date(2023, 2, 15), descricao='Salario Fev')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta2, tipo='D', valor=Decimal('300'), data_caixa=date(2023, 2, 20), data_competencia=date(2023, 2, 20), descricao='Mercado Fev')
        
        # Durante Março
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('100'), data_caixa=date(2023, 3, 5), data_competencia=date(2023, 3, 5), descricao='Lanche')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta2, tipo='C', valor=Decimal('50'), data_caixa=date(2023, 3, 10), data_competencia=date(2023, 3, 10), descricao='Reembolso')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('200'), data_caixa=date(2023, 3, 10), data_competencia=date(2023, 3, 10), descricao='Cinema')

        # --- Lançamentos para teste de categorias (Mês de Abril/2023) ---
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('1000'), categoria=cls.cat_moradia, data_competencia=date(2023, 4, 5), data_caixa=date(2023, 4, 5), descricao='Aluguel Abr')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('500'), categoria=cls.cat_alimentacao, data_competencia=date(2023, 4, 10), data_caixa=date(2023, 4, 10), descricao='Supermercado')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('300'), categoria=cls.cat_transporte, data_competencia=date(2023, 4, 12), data_caixa=date(2023, 4, 12), descricao='Gasolina')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('200'), categoria=cls.cat_lazer, data_competencia=date(2023, 4, 15), data_caixa=date(2023, 4, 15), descricao='Show')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('150'), categoria=cls.cat_saude, data_competencia=date(2023, 4, 18), data_caixa=date(2023, 4, 18), descricao='Farmácia')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('100'), categoria=cls.cat_educacao, data_competencia=date(2023, 4, 20), data_caixa=date(2023, 4, 20), descricao='Livro')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('50'), categoria=cls.cat_alimentacao, data_competencia=date(2023, 4, 22), data_caixa=date(2023, 4, 22), descricao='Padaria')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='D', valor=Decimal('20'), categoria=None, data_competencia=date(2023, 4, 25), data_caixa=date(2023, 4, 25), descricao='Estacionamento')
        Lancamento.objects.create(usuario=cls.user, conta_bancaria=cls.conta1, tipo='C', valor=Decimal('5000'), categoria=cls.cat_salario, data_competencia=date(2023, 4, 1), data_caixa=date(2023, 4, 1), descricao='Salario Abr') # Crédito, deve ser ignorado no gráfico de despesas

    def test_gerar_dados_grafico_saldo(self):
        """
        Testa se o gráfico de evolução de saldo é gerado corretamente.
        """
        labels, data = gerar_dados_grafico_saldo(self.user, 2023, 3)

        # Saldo inicial em 01/Mar/2023:
        # Conta 1: 1000 (inicial) + 2000 - 800 + 2000 = 4200
        # Conta 2: 500 (inicial) - 300 = 200
        # Total: 4400
        saldo_inicial_mar = 4400.0

        # Evolução em Março:
        # Dia 05: 4400 - 100 = 4300
        # Dia 10: 4300 + 50 - 200 = 4150
        
        self.assertEqual(len(labels), 31) # Março tem 31 dias
        self.assertEqual(len(data), 31)
        
        # Verifica o saldo inicial (primeiro ponto do gráfico)
        self.assertAlmostEqual(data[0], saldo_inicial_mar)
        
        # Verifica pontos chave
        self.assertAlmostEqual(data[3], saldo_inicial_mar) # Dia 4
        self.assertAlmostEqual(data[4], 4300.0) # Dia 5
        self.assertAlmostEqual(data[8], 4300.0) # Dia 9
        self.assertAlmostEqual(data[9], 4150.0) # Dia 10
        
        # Verifica o último dia
        self.assertAlmostEqual(data[-1], 4150.0)

    def test_gerar_dados_grafico_categorias(self):
        """
        Testa se o gráfico de despesas por categoria é gerado corretamente.
        """
        dados = gerar_dados_grafico_categorias(self.user, 2023, 4)

        # Totais esperados:
        # Moradia: 1000, Alimentação: 550, Transporte: 300, Lazer: 200,
        # Saúde: 150, Educação: 100, Sem Categoria: 20
        
        # Visão Completa
        esperado_completo = {
            'labels': ['Moradia', 'Alimentação', 'Transporte', 'Lazer', 'Saúde', 'Educação', 'Sem Categoria'],
            'data': [1000.0, 550.0, 300.0, 200.0, 150.0, 100.0, 20.0]
        }
        self.assertEqual(dados['completo'], esperado_completo)

        # Visão Condensada (Top 5 + Outros)
        # Outros = Educação (100) + Sem Categoria (20) = 120
        esperado_condensado = {
            'labels': ['Moradia', 'Alimentação', 'Transporte', 'Lazer', 'Saúde', 'Outros'],
            'data': [1000.0, 550.0, 300.0, 200.0, 150.0, 120.0]
        }
        self.assertEqual(dados['condensado'], esperado_condensado)

    def test_grafico_saldo_sem_contas(self):
        """
        Testa o comportamento do gráfico de saldo para um usuário sem contas.
        """
        user_sem_conta = User.objects.create_user(username='semconta', password='password123')
        labels, data = gerar_dados_grafico_saldo(user_sem_conta, 2023, 1)
        self.assertEqual(labels, [])
        self.assertEqual(data, [])

    def test_grafico_categorias_sem_despesas(self):
        """
        Testa o comportamento do gráfico de categorias para um mês sem despesas.
        """
        # Maio de 2023 não tem despesas cadastradas
        dados = gerar_dados_grafico_categorias(self.user, 2023, 5)
        self.assertEqual(dados, {})

    def test_grafico_categorias_menos_de_cinco(self):
        """
        Testa o gráfico de categorias quando há menos de 5 categorias com despesas.
        """
        user_pocas_cat = User.objects.create_user(username='poucacat', password='password123')
        conta = ContaBancaria.objects.create(
            usuario=user_pocas_cat, nome_banco='Banco C', numero_conta='333',
            saldo_inicial=0, data_saldo_inicial=date(2023, 1, 1)
        )
        cat1 = Categoria.objects.create(nome='Cat A', usuario=user_pocas_cat)
        cat2 = Categoria.objects.create(nome='Cat B', usuario=user_pocas_cat)

        Lancamento.objects.create(usuario=user_pocas_cat, conta_bancaria=conta, tipo='D', valor=100, categoria=cat1, data_competencia=date(2023, 6, 5), data_caixa=date(2023, 6, 5), descricao='Gasto A')
        Lancamento.objects.create(usuario=user_pocas_cat, conta_bancaria=conta, tipo='D', valor=200, categoria=cat2, data_competencia=date(2023, 6, 10), data_caixa=date(2023, 6, 10), descricao='Gasto B')

        dados = gerar_dados_grafico_categorias(user_pocas_cat, 2023, 6)

        # Espera-se que a visão condensada seja igual à completa, sem a categoria "Outros"
        esperado = {
            'labels': ['Cat B', 'Cat A'],
            'data': [200.0, 100.0]
        }
        self.assertEqual(dados['completo'], esperado)
        self.assertEqual(dados['condensado'], esperado)
