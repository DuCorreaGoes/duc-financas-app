from datetime import datetime
import json
import os
import time
from collections import defaultdict
from calendar import month_name
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle


class DucFinancasApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.historico = []
        self.saldo_total = 0.0
        self.arquivo_dados = "duc_financas_dados.json"
        self.arquivo_config = "duc_financas_config.json"

    def build(self):
        self.title = "DuC Finanças"

        # Carrega dados salvos
        self.carregar_dados()

        # Layout principal
        main_layout = BoxLayout(orientation='vertical', spacing=dp(5), padding=dp(10))

        # Cabeçalho
        header = self.criar_cabecalho()
        main_layout.add_widget(header)

        # Painel com abas
        self.tab_panel = TabbedPanel(do_default_tab=False)
        self.tab_panel.tab_pos = 'top_mid'

        # Aba Transações
        tab_transacoes = TabbedPanelItem(text='Transações')
        tab_transacoes.content = self.criar_aba_transacoes()
        self.tab_panel.add_widget(tab_transacoes)

        # Aba Análise
        tab_analise = TabbedPanelItem(text='Análise')
        tab_analise.content = self.criar_aba_analise()
        self.tab_panel.add_widget(tab_analise)

        main_layout.add_widget(self.tab_panel)

        # Atualiza exibições iniciais
        self.atualizar_saldo()
        self.atualizar_historico()
        Clock.schedule_once(lambda dt: self.gerar_analise(), 0.1)

        return main_layout

    def criar_cabecalho(self):
        """Cria o cabeçalho com título e saldo"""
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80))

        # Título
        titulo = Label(
            text='DuC Finanças',
            font_size='20sp',
            bold=True,
            size_hint_y=None,
            height=dp(40)
        )
        header.add_widget(titulo)

        # Saldo
        self.label_saldo = Label(
            text=f'Saldo Total: R$ {self.saldo_total:.2f}',
            font_size='16sp',
            bold=True,
            size_hint_y=None,
            height=dp(40)
        )
        header.add_widget(self.label_saldo)

        return header

    def criar_aba_transacoes(self):
        """Cria a aba de transações"""
        layout = BoxLayout(orientation='vertical', spacing=dp(1))

        # Formulário de entrada
        form_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(180))

        form_layout.add_widget(Label(text='Nova Transação', font_size='16sp', bold=True,
                                     size_hint_y=None, height=dp(60)))

        # Campo valor
        self.input_valor = TextInput(
            hint_text='Ex: +100 ou -50',
            multiline=False,
            input_filter='float',
            size_hint_y=None,
            height=dp(40)
        )
        form_layout.add_widget(self.input_valor)

        # Campo descrição
        self.input_descricao = TextInput(
            hint_text='Ex: Salário, Mercado...',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        form_layout.add_widget(self.input_descricao)

        # Botões
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))

        btn_adicionar = Button(text='Adicionar', size_hint_x=0.7)
        btn_adicionar.bind(on_press=self.adicionar_transacao)
        btn_layout.add_widget(btn_adicionar)

        btn_limpar = Button(text='Limpar', size_hint_x=0.3)
        btn_limpar.bind(on_press=self.confirmar_limpeza)
        btn_layout.add_widget(btn_limpar)

        form_layout.add_widget(btn_layout)
        layout.add_widget(form_layout)

        # SOLUÇÃO 3: Container do histórico SEM padding e SEM spacing
        historico_container = BoxLayout(
            orientation='vertical',
            spacing=0,
            size_hint_y=1,
            padding=0
        )

        # Título "Histórico"
        historico_container.add_widget(Label(
            text='Histórico',
            font_size='16sp',
            bold=True,
            size_hint_y=None,
            height=dp(30)
        ))

        # ScrollView SEM barra de rolagem e SEM padding
        scroll = ScrollView(bar_width=0)

        # Layout da lista SEM spacing e SEM padding
        self.historico_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=0,  # SOLUÇÃO 1: Remove espaço entre itens
            padding=0  # SOLUÇÃO 2: Remove padding interno
        )

        self.historico_layout.bind(minimum_height=self.historico_layout.setter('height'))
        scroll.add_widget(self.historico_layout)
        historico_container.add_widget(scroll)

        layout.add_widget(historico_container)

        return layout

    def criar_aba_analise(self):
        """Cria a aba de análise"""
        layout = BoxLayout(orientation='vertical', spacing=dp(10))

        # Título
        layout.add_widget(Label(text='Análise de Gastos', font_size='16sp', bold=True,
                                size_hint_y=None, height=dp(40)))

        # ScrollView para análise
        scroll = ScrollView()
        self.analise_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.analise_layout.bind(minimum_height=self.analise_layout.setter('height'))
        scroll.add_widget(self.analise_layout)
        layout.add_widget(scroll)

        return layout

    def mostrar_toast(self, mensagem):
        """Mostra uma mensagem toast"""
        popup = Popup(
            title='',
            content=Label(text=mensagem),
            size_hint=(0.8, 0.3),
            auto_dismiss=True
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

    def carregar_dados(self):
        """Carrega os dados salvos do arquivo"""
        if os.path.exists(self.arquivo_dados):
            try:
                with open(self.arquivo_dados, 'r', encoding='utf-8') as f:
                    self.historico = json.load(f)
                # Garante que todas as transações tenham ID único
                for i, transacao in enumerate(self.historico):
                    if "id" not in transacao:
                        transacao["id"] = int(time.time() * 1000000) + i
                self.salvar_dados()
                print(f"Dados carregados: {len(self.historico)} transações")
            except Exception as e:
                print(f"Erro ao carregar dados: {e}")
                self.historico = []
        else:
            self.historico = []

    def salvar_dados(self):
        """Salva os dados no arquivo"""
        try:
            with open(self.arquivo_dados, 'w', encoding='utf-8') as f:
                json.dump(self.historico, f, ensure_ascii=False, indent=2)
            print("Dados salvos com sucesso!")
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")

    def atualizar_saldo(self):
        """Atualiza o saldo total"""
        self.saldo_total = sum(item["valor"] for item in self.historico)
        self.label_saldo.text = f'Saldo Total: R$ {self.saldo_total:.2f}'

        # Muda cor baseado no saldo
        if self.saldo_total >= 0:
            self.label_saldo.color = get_color_from_hex('#4CAF50')  # Verde
        else:
            self.label_saldo.color = get_color_from_hex('#F44336')  # Vermelho

    def adicionar_transacao(self, instance):
        """Adiciona uma nova transação"""
        try:
            valor_texto = self.input_valor.text.strip()
            descricao = self.input_descricao.text.strip()

            if not valor_texto or not descricao:
                self.mostrar_toast("Preencha todos os campos!")
                return

            valor = float(valor_texto)

            transacao = {
                "id": int(time.time() * 1000000) + len(self.historico),
                "valor": valor,
                "descricao": descricao,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            }

            self.historico.append(transacao)
            self.salvar_dados()
            self.atualizar_historico()
            self.atualizar_saldo()
            self.gerar_analise()

            # Limpa campos
            self.input_valor.text = ""
            self.input_descricao.text = ""

            tipo = "Receita" if valor > 0 else "Gasto"
            self.mostrar_toast(f"{tipo} adicionado!")

        except ValueError:
            self.mostrar_toast("Valor deve ser um número!")
        except Exception as e:
            self.mostrar_toast(f"Erro: {e}")

    def atualizar_historico(self):
        """Atualiza a exibição do histórico"""
        self.historico_layout.clear_widgets()

        for transacao in reversed(self.historico):
            self.criar_item_historico(transacao)

    def criar_item_historico(self, transacao):
        """Cria um item do histórico"""
        # Layout do item
        item_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(60),
            spacing=dp(5)
        )

        # Canvas com fundo - VERSÃO CORRIGIDA
        with item_layout.canvas.before:
            Color(0.1, 0.1, 0.1, 1)  # Cinza muito escuro
            item_rect = Rectangle(size=item_layout.size, pos=item_layout.pos)

        # Função update específica para este item
        def update_item_rect(instance, value):
            item_rect.pos = instance.pos
            item_rect.size = instance.size

        item_layout.bind(pos=update_item_rect, size=update_item_rect)

        # Informações da transação
        info_layout = BoxLayout(orientation='vertical', size_hint_x=0.7)

        # Descrição
        label_desc = Label(
            text=transacao["descricao"],
            font_size='14sp',
            bold=True,
            text_size=(None, None),
            halign='left'
        )
        info_layout.add_widget(label_desc)

        # Valor e data
        valor = transacao["valor"]
        simbolo = "+" if valor > 0 else ""
        cor_valor = get_color_from_hex('#4CAF50') if valor > 0 else get_color_from_hex('#F44336')

        detalhes_layout = BoxLayout(orientation='horizontal')

        label_valor = Label(
            text=f'R$ {simbolo}{valor:.2f}',
            font_size='12sp',
            bold=True,
            color=cor_valor,
            size_hint_x=0.6
        )
        detalhes_layout.add_widget(label_valor)

        label_data = Label(
            text=transacao["data"].split(' ')[0],  # Só a data
            font_size='10sp',
            color=get_color_from_hex('#666666'),
            size_hint_x=0.4
        )
        detalhes_layout.add_widget(label_data)

        info_layout.add_widget(detalhes_layout)
        item_layout.add_widget(info_layout)

        # Botões de ação
        botoes_layout = BoxLayout(orientation='horizontal', size_hint_x=0.3)

        btn_editar = Button(
            text='EDIT',
            size_hint_x=0.5,
            font_size='16sp',
            color=get_color_from_hex('#64B5F6')
        )
        btn_editar.bind(on_press=lambda x: self.editar_transacao(transacao["id"]))
        botoes_layout.add_widget(btn_editar)

        btn_excluir = Button(
            text='X',
            size_hint_x=0.5,
            font_size='23sp',
            color=get_color_from_hex('#F44336')
        )
        btn_excluir.bind(on_press=lambda x: self.confirmar_exclusao(transacao["id"]))
        botoes_layout.add_widget(btn_excluir)

        item_layout.add_widget(botoes_layout)

        self.historico_layout.add_widget(item_layout)

    def encontrar_transacao_por_id(self, transacao_id):
        """Encontra uma transação pelo ID"""
        for i, transacao in enumerate(self.historico):
            if transacao.get("id") == transacao_id:
                return i, transacao
        return -1, None

    def editar_transacao(self, transacao_id):
        """Edita uma transação"""
        indice, transacao = self.encontrar_transacao_por_id(transacao_id)
        if transacao is None:
            self.mostrar_toast("Transação não encontrada!")
            return

        # Layout do popup
        content = BoxLayout(orientation='vertical', spacing=dp(10))

        # Campos de edição
        input_valor = TextInput(
            text=str(transacao["valor"]),
            hint_text='Valor',
            multiline=False,
            input_filter='float',
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(input_valor)

        input_desc = TextInput(
            text=transacao["descricao"],
            hint_text='Descrição',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(input_desc)

        # Botões
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))

        def salvar_edicao(instance):
            try:
                novo_valor = float(input_valor.text)
                nova_desc = input_desc.text.strip()

                if not nova_desc:
                    self.mostrar_toast("Descrição não pode estar vazia!")
                    return

                self.historico[indice]["valor"] = novo_valor
                self.historico[indice]["descricao"] = nova_desc
                self.historico[indice]["data_edicao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

                self.salvar_dados()
                self.atualizar_historico()
                self.atualizar_saldo()
                self.gerar_analise()

                popup.dismiss()
                self.mostrar_toast("Transação editada!")

            except ValueError:
                self.mostrar_toast("Valor deve ser um número!")
            except Exception as e:
                self.mostrar_toast(f"Erro: {e}")

        btn_salvar = Button(text='Salvar')
        btn_salvar.bind(on_press=salvar_edicao)
        btn_layout.add_widget(btn_salvar)

        btn_cancelar = Button(text='Cancelar')
        btn_cancelar.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_cancelar)

        content.add_widget(btn_layout)

        popup = Popup(
            title='Editar Transação',
            content=content,
            size_hint=(0.9, 0.4)
        )
        popup.open()

    def confirmar_exclusao(self, transacao_id):
        """Confirma a exclusão de uma transação"""
        indice, transacao = self.encontrar_transacao_por_id(transacao_id)
        if transacao is None:
            self.mostrar_toast("Transação não encontrada!")
            return

        # Layout do popup
        content = BoxLayout(orientation='vertical', spacing=dp(10))

        content.add_widget(Label(
            text=f"Excluir '{transacao['descricao']}'\n(R$ {transacao['valor']:.2f})?",
            text_size=(dp(250), None),
            halign='center'
        ))

        # Botões
        btn_layout = BoxLayout(orientation='horizontal')

        def excluir(instance):
            try:
                self.historico.pop(indice)
                self.salvar_dados()
                self.atualizar_historico()
                self.atualizar_saldo()
                self.gerar_analise()
                popup.dismiss()
                self.mostrar_toast("Transação excluída!")
            except Exception as e:
                self.mostrar_toast(f"Erro: {e}")

        btn_excluir = Button(text='Excluir')
        btn_excluir.bind(on_press=excluir)
        btn_layout.add_widget(btn_excluir)

        btn_cancelar = Button(text='Cancelar')
        btn_cancelar.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_cancelar)

        content.add_widget(btn_layout)

        popup = Popup(
            title='Confirmar Exclusão',
            content=content,
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def confirmar_limpeza(self, instance):
        """Confirma a limpeza de todo o histórico"""
        content = BoxLayout(orientation='vertical', spacing=dp(10))

        content.add_widget(Label(
            text="Tem certeza que deseja\nlimpar todo o histórico?",
            halign='center'
        ))

        btn_layout = BoxLayout(orientation='horizontal')

        def limpar(instance):
            self.historico.clear()
            self.salvar_dados()
            self.atualizar_historico()
            self.atualizar_saldo()
            self.gerar_analise()
            popup.dismiss()
            self.mostrar_toast("Histórico limpo!")

        btn_limpar = Button(text='Limpar')
        btn_limpar.bind(on_press=limpar)
        btn_layout.add_widget(btn_limpar)

        btn_cancelar = Button(text='Cancelar')
        btn_cancelar.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_cancelar)

        content.add_widget(btn_layout)

        popup = Popup(
            title='Confirmar Limpeza',
            content=content,
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def gerar_analise(self):
        """Gera a análise de gastos"""
        self.analise_layout.clear_widgets()

        # Analisa gastos por tópico e mês
        dados_analise = defaultdict(lambda: defaultdict(lambda: {"quantidade": 0, "total": 0.0}))

        for transacao in self.historico:
            if transacao["valor"] < 0:  # Apenas gastos
                try:
                    data_str = transacao["data"].split(" ")[0]
                    dia, mes, ano = data_str.split("/")

                    chave_mes = f"{ano}-{mes.zfill(2)}"
                    topico = transacao["descricao"].lower().strip()

                    dados_analise[chave_mes][topico]["quantidade"] += 1
                    dados_analise[chave_mes][topico]["total"] += abs(transacao["valor"])

                except Exception as e:
                    print(f"Erro ao processar transação: {e}")
                    continue

        if not dados_analise:
            self.analise_layout.add_widget(Label(
                text="Nenhum gasto encontrado para análise.",
                halign='center'
            ))
            return

        # Ordena meses (mais recentes primeiro)
        meses_ordenados = sorted(dados_analise.keys(), reverse=True)

        for mes_key in meses_ordenados:
            ano, mes = mes_key.split("-")
            nome_mes = month_name[int(mes)] if int(mes) <= 12 else "Mês inválido"

            # Container do mês
            mes_layout = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                spacing=dp(5),
                padding=dp(10)
            )

            # Canvas com fundo
            with mes_layout.canvas.before:
                Color(0.1, 0.1, 0, 1)
                self.rect_mes = Rectangle(size=mes_layout.size, pos=mes_layout.pos)

            def update_rect_mes(instance, value):
                self.rect_mes.pos = instance.pos
                self.rect_mes.size = instance.size

            mes_layout.bind(pos=update_rect_mes, size=update_rect_mes)

            # Título do mês
            total_mes = sum(info['total'] for info in dados_analise[mes_key].values())
            total_transacoes = sum(info['quantidade'] for info in dados_analise[mes_key].values())

            mes_layout.add_widget(Label(
                text=f"{nome_mes} {ano}\n{len(dados_analise[mes_key])} categorias | {total_transacoes} transações | R$ {total_mes:.2f}",
                font_size='14sp',
                bold=True,
                size_hint_y=None,
                height=dp(50),
                halign='center'
            ))

            # Ordena tópicos por quantidade
            topicos_ordenados = sorted(
                dados_analise[mes_key].items(),
                key=lambda x: x[1]["quantidade"],
                reverse=True
            )

            # Lista os tópicos
            for topico, info in topicos_ordenados:
                item_layout = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(30)
                )

                item_layout.add_widget(Label(
                    text=topico.title(),
                    font_size='12sp',
                    size_hint_x=0.5,
                    halign='left'
                ))

                item_layout.add_widget(Label(
                    text=f"{info['quantidade']}x",
                    font_size='11sp',
                    size_hint_x=0.2,
                    halign='center',
                    color=get_color_from_hex('#2196F3')  # Azul
                ))

                item_layout.add_widget(Label(
                    text=f"R$ {info['total']:.2f}",
                    font_size='11sp',
                    size_hint_x=0.3,
                    bold=True,
                    halign='right',
                    color=get_color_from_hex('#F44336')  # Vermelho
                ))

                mes_layout.add_widget(item_layout)

            # Calcula altura do layout do mês
            altura_mes = dp(50) + (len(topicos_ordenados) * dp(30)) + dp(20)
            mes_layout.height = altura_mes

            self.analise_layout.add_widget(mes_layout)

            # Separador
            self.analise_layout.add_widget(Label(text='', size_hint_y=None, height=dp(10)))

# Executa o app
if __name__ == "__main__":
    DucFinancasApp().run()