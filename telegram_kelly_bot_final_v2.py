#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - Calculadora de Kelly
Versão Final v2 com Pergunta sobre Juice
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class KellyCalculator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.step = 'start'
        self.has_opposite_market = None
        self.is_juice_free = None
        self.fair_odds = None
        self.opposite_odds = None
        self.value_odds = None

    def start_conversation(self):
        self.step = 'opposite_market'
        return "❓ **O mercado que deseja apostar tem mercado contrário?**"

    def process_message(self, message):
        response = message.lower().strip()

        if self.step == 'opposite_market':
            if response in ['sim', 's', 'yes', 'y']:
                self.has_opposite_market = True
                self.step = 'fair_odds'
                return "📊 **Qual a odd justa?** (Ex: 1.66)"
            elif response in ['não', 'nao', 'n', 'no']:
                self.has_opposite_market = False
                self.step = 'juice_question'
                return "🔍 **A odd de referência já está sem juice?**"
            else:
                return "❌ Por favor, responda 'Sim' ou 'Não'"

        elif self.step == 'juice_question':
            if response in ['sim', 's', 'yes', 'y']:
                self.is_juice_free = True
                self.step = 'fair_odds_no_opposite'
                return "📊 **Qual a odd de referência (sem juice)?** (Ex: 2.38)"
            elif response in ['não', 'nao', 'n', 'no']:
                self.is_juice_free = False
                self.step = 'fair_odds_no_opposite'
                return "📊 **Qual a odd justa encontrada?** (Ex: 2.00)"
            else:
                return "❌ Por favor, responda 'Sim' ou 'Não'"

        elif self.step in ['fair_odds', 'fair_odds_no_opposite']:
            try:
                fair_odds = float(message.replace(',', '.'))
                if fair_odds <= 1.0:
                    return "❌ Por favor, digite um número válido maior que 1.0"
                self.fair_odds = fair_odds
                
                if self.has_opposite_market:
                    self.step = 'opposite_odds'
                    return "📈 **Qual a odd do mercado contrário?** (Ex: 2.20)"
                else:
                    self.step = 'value_odds_no_opposite'
                    return "💰 **Qual a odd de valor encontrada?** (Ex: 2.65)"
            except ValueError:
                return "❌ Por favor, digite um número válido"

        elif self.step == 'opposite_odds':
            try:
                opposite_odds = float(message.replace(',', '.'))
                if opposite_odds <= 1.0:
                    return "❌ Por favor, digite um número válido maior que 1.0"
                self.opposite_odds = opposite_odds
                self.step = 'value_odds'
                return "💰 **Qual a odd de valor encontrada?** (Ex: 2.00)"
            except ValueError:
                return "❌ Por favor, digite um número válido"

        elif self.step in ['value_odds', 'value_odds_no_opposite']:
            try:
                value_odds = float(message.replace(',', '.'))
                if value_odds <= 1.0:
                    return "❌ Por favor, digite um número válido maior que 1.0"
                self.value_odds = value_odds
                self.step = 'completed'
                return self.calculate_result()
            except ValueError:
                return "❌ Por favor, digite um número válido"

        else:
            return "❌ Erro interno. Use /calcular para começar novamente."

    def calculate_result(self):
        if self.has_opposite_market:
            # Passo 1: Calcular probabilidades implícitas
            p_fair = 1 / self.fair_odds
            p_opposite = 1 / self.opposite_odds
            
            # Passo 2: Calcular soma das probabilidades (com juice)
            total_prob = p_fair + p_opposite
            
            # Passo 3: Calcular probabilidades reais (sem juice)
            real_prob = p_fair / total_prob
        else:
            # Sem mercado contrário - verificar se precisa ajustar juice
            if self.is_juice_free:
                # Odd já está sem juice - usar diretamente
                real_prob = 1 / self.fair_odds
            else:
                # Odd com juice - adicionar 0.15 para estimar sem juice
                adjusted_fair_odds = self.fair_odds + 0.15
                real_prob = 1 / adjusted_fair_odds

        # Passo 5: Calcular lucro líquido (b)
        b = self.value_odds - 1
        
        # Passo 6: Calcular valor esperado (EV)
        expected_value = real_prob * b - (1 - real_prob)
        
        # Passo 7: Calcular fração de Kelly cheia
        kelly_full = expected_value / b
        
        # Passo 8: Calcular stake conservadora (1/8 Kelly)
        kelly_conservative = kelly_full / 8
        
        # Converter para porcentagem e arredondar para 2 casas decimais
        stake_percent = round(kelly_conservative * 100, 2)

        return self.format_result(stake_percent)

    def format_result(self, final_stake):
        # Verificar se tem valor mínimo de 0.5%
        if final_stake < 0.5:
            return "❌ **APOSTA SEM VALOR**\n\nA odd não apresenta valor explícito para apostar.\n\n⚠️ **Aposte sempre com responsabilidade!**"

        output = "📊 **DADOS DE ENTRADA:**\n"
        if self.has_opposite_market:
            output += f"• Odd Justa: {self.fair_odds}\n"
            output += f"• Odd Contrária: {self.opposite_odds}\n"
            output += f"• Odd de Valor: {self.value_odds}\n"
        else:
            if self.is_juice_free:
                output += f"• Odd de Referência (sem juice): {self.fair_odds}\n"
            else:
                output += f"• Odd Justa: {self.fair_odds}\n"
            output += f"• Odd de Valor: {self.value_odds}\n"
        
        output += "\n🎯 **RECOMENDAÇÃO FINAL:**\n"
        output += f"💰 **Stake recomendada: {final_stake:.2f}%**\n"
        
        output += "\n✅ **APOSTA COM VALOR CONFIRMADA!**\n"
        output += "\n⚠️ **Aposte sempre com responsabilidade!**"
        
        return output

# Dicionário para armazenar calculadoras por usuário
user_calculators = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    keyboard = [
        [InlineKeyboardButton("🧮 Calcular Kelly", callback_data='calcular')],
        [InlineKeyboardButton("📊 Ver Exemplo", callback_data='exemplo')],
        [InlineKeyboardButton("❓ Ajuda", callback_data='ajuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """🎯 **Calculadora de Kelly - CoreQuantikAI**

Olá! Sou sua calculadora de Kelly profissional.

Vou te ajudar a calcular a stake ideal para suas apostas usando o critério de Kelly conservador.

**Escolha uma opção abaixo:**"""

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def calcular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /calcular"""
    user_id = update.effective_user.id
    user_calculators[user_id] = KellyCalculator()
    
    response = user_calculators[user_id].start_conversation()
    
    keyboard = [
        [InlineKeyboardButton("✅ Sim", callback_data='sim')],
        [InlineKeyboardButton("❌ Não", callback_data='nao')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

async def exemplo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /exemplo"""
    exemplo_text = """📊 **EXEMPLOS DE CÁLCULO**

🔹 **Exemplo 1: Com mercado contrário**
❓ Tem mercado contrário? **SIM**
📊 Odd justa: **1.66**
📈 Odd contrária: **2.20**
💰 Odd de valor: **2.50**
🎯 Resultado: **3.54% da banca**

🔹 **Exemplo 2: Sem mercado contrário + com juice**
❓ Tem mercado contrário? **NÃO**
🔍 Odd sem juice? **NÃO**
📊 Odd justa: **2.00**
💰 Odd de valor: **3.25**
🎯 Resultado: **2.84% da banca**

🔹 **Exemplo 3: Sem mercado contrário + sem juice**
❓ Tem mercado contrário? **NÃO**
🔍 Odd sem juice? **SIM**
📊 Odd referência: **2.38**
💰 Odd de valor: **2.65**
🎯 Resultado: **0.86% da banca**

💡 **Use /calcular para fazer sua análise!**"""

    await update.message.reply_text(exemplo_text, parse_mode='Markdown')

async def ajuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda"""
    ajuda_text = """❓ **COMO USAR A CALCULADORA**

**Comandos disponíveis:**
• `/start` - Iniciar o bot
• `/calcular` - Nova análise de Kelly
• `/exemplo` - Ver exemplos práticos
• `/ajuda` - Esta mensagem

**Como funciona:**
1️⃣ Use `/calcular` para iniciar
2️⃣ Responda se tem mercado contrário
3️⃣ Se não tiver, responda se a odd está sem juice
4️⃣ Digite as odds solicitadas
5️⃣ Receba a stake recomendada

**Tipos de cálculo:**
🔸 **Com mercado contrário:** Remove juice usando ambas odds
🔸 **Sem mercado + com juice:** Adiciona 0.15 para estimar
🔸 **Sem mercado + sem juice:** Usa odd diretamente

**Sobre o cálculo:**
• Usa critério de Kelly conservador (÷8)
• Remove juice das casas de apostas
• Só recomenda apostas com valor real
• Mínimo de 0.5% para recomendar

**Responsabilidade:**
⚠️ Aposte sempre com responsabilidade
💰 Nunca aposte mais do que pode perder
📊 Use apenas como ferramenta de análise"""

    await update.message.reply_text(ajuda_text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para botões inline"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'calcular':
        user_calculators[user_id] = KellyCalculator()
        response = user_calculators[user_id].start_conversation()
        
        keyboard = [
            [InlineKeyboardButton("✅ Sim", callback_data='sim')],
            [InlineKeyboardButton("❌ Não", callback_data='nao')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'exemplo':
        await exemplo_command(query, context)
    
    elif query.data == 'ajuda':
        await ajuda_command(query, context)
    
    elif query.data in ['sim', 'nao']:
        if user_id not in user_calculators:
            await query.edit_message_text("❌ Sessão expirada. Use /calcular para começar novamente.")
            return
        
        response_text = 'sim' if query.data == 'sim' else 'não'
        response = user_calculators[user_id].process_message(response_text)
        
        # Se for a pergunta sobre juice, adicionar botões
        if user_calculators[user_id].step == 'juice_question':
            keyboard = [
                [InlineKeyboardButton("✅ Sim", callback_data='sim')],
                [InlineKeyboardButton("❌ Não", callback_data='nao')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.edit_message_text(response, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processar mensagens de texto"""
    user_id = update.effective_user.id
    
    if user_id not in user_calculators:
        keyboard = [
            [InlineKeyboardButton("🧮 Calcular Kelly", callback_data='calcular')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Olá! Use /calcular para iniciar uma nova análise.",
            reply_markup=reply_markup
        )
        return
    
    calculator = user_calculators[user_id]
    response = calculator.process_message(update.message.text)
    
    # Se completou o cálculo, limpar a sessão
    if calculator.step == 'completed':
        keyboard = [
            [InlineKeyboardButton("🔄 Nova Análise", callback_data='calcular')],
            [InlineKeyboardButton("📊 Ver Exemplo", callback_data='exemplo')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        del user_calculators[user_id]
    else:
        await update.message.reply_text(response, parse_mode='Markdown')

def main():
    """Função principal"""
    # SUBSTITUA PELO SEU TOKEN DO BOT
    TOKEN = "7011621003:AAFyJllQTNesTvI8CQoovkQQIn4f_e3VjGk"
    
    # Criar aplicação
    application = Application.builder().token(TOKEN).build()
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("calcular", calcular_command))
    application.add_handler(CommandHandler("exemplo", exemplo_command))
    application.add_handler(CommandHandler("ajuda", ajuda_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Iniciar bot
    print("🤖 Bot Telegram iniciado!")
    print("📊 Calculadora de Kelly v2 ativa!")
    print("🔍 Nova funcionalidade: Pergunta sobre juice implementada!")
    application.run_polling()

if __name__ == '__main__':
    main()

