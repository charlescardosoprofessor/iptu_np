#!/usr/bin/env python3
"""
Script para criar uma planilha Excel de exemplo com dados de boletos
para demonstração da aplicação STER CONTRATANTE (Versão Atualizada).
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def gerar_codigo_barras():
    """Gera um código de barras fictício de 44 dígitos."""
    # Código de barras padrão brasileiro tem 44 dígitos
    # Formato: BBBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
    # BBB = código do banco (3 dígitos)
    # V = dígito verificador (1 dígito)
    # Restante = campo livre (40 dígitos)
    
    banco = random.choice(['001', '033', '104', '237', '341', '389', '422'])  # Códigos de bancos reais
    digito_verificador = str(random.randint(0, 9))
    campo_livre = ''.join([str(random.randint(0, 9)) for _ in range(40)])
    
    return banco + digito_verificador + campo_livre

def gerar_cpf():
    """Gera um CPF fictício válido."""
    def calcular_digito(cpf_parcial):
        soma = 0
        for i, digito in enumerate(cpf_parcial):
            soma += int(digito) * (len(cpf_parcial) + 1 - i)
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)
    
    # Gerar 9 primeiros dígitos
    cpf_base = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    
    # Calcular primeiro dígito verificador
    primeiro_digito = calcular_digito(cpf_base)
    
    # Calcular segundo dígito verificador
    segundo_digito = calcular_digito(cpf_base + primeiro_digito)
    
    cpf_completo = cpf_base + primeiro_digito + segundo_digito
    
    # Formatar CPF
    return f"{cpf_completo[:3]}.{cpf_completo[3:6]}.{cpf_completo[6:9]}-{cpf_completo[9:]}"

def create_sample_boletos():
    """Cria dados de exemplo para boletos com códigos de barras e CPFs."""
    
    # Lista de nomes fictícios para os devedores
    nomes_devedores = [
        "João Silva Santos",
        "Maria Oliveira Costa",
        "Pedro Almeida Ferreira",
        "Ana Paula Rodrigues",
        "Carlos Eduardo Lima",
        "Fernanda Souza Pereira",
        "Roberto Carlos Mendes",
        "Juliana Martins Barbosa",
        "Ricardo Henrique Dias",
        "Patrícia Gomes Nascimento",
        "Marcos Antonio Ribeiro",
        "Luciana Fernandes Araújo",
        "André Luiz Cardoso",
        "Camila Cristina Moreira",
        "Felipe Augusto Correia",
        "Beatriz Santos Silva",
        "Gabriel Costa Oliveira",
        "Larissa Pereira Lima",
        "Thiago Rodrigues Almeida",
        "Vanessa Martins Ferreira"
    ]
    
    # Gerar dados de exemplo
    boletos = []
    
    for i in range(50):  # Criar 50 boletos de exemplo
        codigo_boleto = f"BOL{str(i+1).zfill(6)}"  # BOL000001, BOL000002, etc.
        codigo_barras = gerar_codigo_barras()  # Código de barras de 44 dígitos
        nome_devedor = random.choice(nomes_devedores)
        cpf_devedor = gerar_cpf()  # CPF válido formatado
        valor = round(random.uniform(50.00, 2000.00), 2)  # Valores entre R$ 50 e R$ 2000
        
        # Data de vencimento aleatória (entre 30 dias atrás e 60 dias à frente)
        dias_aleatorio = random.randint(-30, 60)
        data_vencimento = datetime.now() + timedelta(days=dias_aleatorio)
        
        # Status do boleto
        status_opcoes = ["Pendente", "Pago", "Vencido", "Cancelado"]
        status = random.choice(status_opcoes)
        
        # Descrição do boleto (focando em IPTU para o exemplo)
        descricoes = [
            "IPTU 2025 - Cota Única",
            "IPTU 2025 - 1ª Parcela",
            "IPTU 2025 - 2ª Parcela",
            "IPTU 2025 - 3ª Parcela",
            "IPTU 2025 - 4ª Parcela",
            "IPTU 2025 - 5ª Parcela",
            "Taxa de Coleta de Lixo 2025",
            "Contribuição de Melhoria",
            "Taxa de Iluminação Pública",
            "Multa de Trânsito"
        ]
        descricao = random.choice(descricoes)
        
        # Identificação do cliente (pode ser diferente do nome do devedor)
        identificacao_cliente = nome_devedor  # Por simplicidade, usando o mesmo nome
        
        boleto = {
            "codigo_boleto": codigo_boleto,
            "codigo_barras": codigo_barras,
            "nome_devedor": nome_devedor,
            "cpf_devedor": cpf_devedor,
            "identificacao_cliente": identificacao_cliente,
            "valor": valor,
            "data_vencimento": data_vencimento.strftime("%d/%m/%Y"),
            "status": status,
            "descricao": descricao,
            "codigo_correios": f"COR{random.randint(300, 999)}"  # Código dos Correios conforme PDF
        }
        
        boletos.append(boleto)
    
    return boletos

def main():
    """Função principal para criar e salvar a planilha."""
    print("Criando dados de exemplo para boletos com códigos de barras...")
    
    # Criar os dados
    boletos = create_sample_boletos()
    
    # Converter para DataFrame
    df = pd.DataFrame(boletos)
    
    # Salvar como Excel
    arquivo_excel = "data/boletos_exemplo.xlsx"
    df.to_excel(arquivo_excel, index=False, sheet_name="Boletos")
    
    print(f"Planilha atualizada criada com sucesso: {arquivo_excel}")
    print(f"Total de boletos criados: {len(boletos)}")
    print("\nPrimeiros 3 registros:")
    print(df.head(3).to_string(index=False))
    print("\nExemplo de código de barras:")
    print(f"Código de barras do primeiro boleto: {boletos[0]['codigo_barras']}")

if __name__ == "__main__":
    main()
