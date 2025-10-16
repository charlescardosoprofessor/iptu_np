from flask import Blueprint, jsonify, request
import pandas as pd
import os
import requests
import threading
import time
import uuid
from datetime import datetime

boletos_bp = Blueprint("boletos", __name__)

# Variáveis globais para armazenar os dados dos boletos e códigos iniciais
dados_boletos = None
codigos_iniciais = {}  # Armazena códigos iniciais por sessão
atendimentos_pendentes = {}  # Armazena atendimentos com status pendente

# URL da API dos Correios (será fornecida pelos Correios em produção)
CORREIOS_API_URL = os.getenv("CORREIOS_API_URL", "https://apphom.correios.com.br/ster/api/v1/atendimentos/registra" )

def carregar_dados_boletos():
    """Carrega os dados da planilha Excel em memória."""
    global dados_boletos
    
    if dados_boletos is None:
        try:
            # Caminho para a planilha Excel
            caminho_arquivo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "boletos_exemplo.xlsx")
            
            # Carregar a planilha
            dados_boletos = pd.read_excel(caminho_arquivo)
            print(f"Dados dos boletos carregados com sucesso. Total de registros: {len(dados_boletos)}")
            
        except FileNotFoundError:
            print(f"Erro: Arquivo de boletos não encontrado em {caminho_arquivo}")
            dados_boletos = pd.DataFrame()  # DataFrame vazio
        except Exception as e:
            print(f"Erro ao carregar dados dos boletos: {e}")
            dados_boletos = pd.DataFrame()  # DataFrame vazio
    
    return dados_boletos

def gerar_codigo_inicial():
    """Gera um código inicial único dos Correios."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    codigo_unico = str(uuid.uuid4())[:8].upper()
    return f"CORR{timestamp}{codigo_unico}"

def converter_valor_para_centavos(valor_decimal):
    """Converte um valor decimal para centavos (inteiro)."""
    return int(valor_decimal * 100)

def processar_atendimento_assincrono(dados_atendimento, codigo_inicial):
    """Processa o atendimento de forma assíncrona, enviando para o API dos Correios."""
    try:
        # Simular tempo de processamento inicial
        time.sleep(1)
        
        # Enviar dados para o API dos Correios
        print(f"Enviando dados para o API dos Correios: {CORREIOS_API_URL}")
        
        # Headers conforme especificação da API dos Correios
        headers = {
            "Content-Type": "application/json",
            "cache-control": "no-cache",
            "Authorization": f"Bearer {os.getenv("CORREIOS_API_TOKEN")}"
        }
        
        response = requests.post(
            CORREIOS_API_URL,
            json=dados_atendimento,
            headers=headers,
            timeout=30
        )
        
        print(f"Status da resposta: {response.status_code}")
        print(f"Conteúdo da resposta: {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            try:
                resultado = response.json()
                
                # A API dos Correios pode retornar diferentes estruturas de resposta
                # Vamos tratar tanto respostas de sucesso quanto de erro
                codigo_interno = resultado.get("codigo") or resultado.get("codigoInterno") or resultado.get("protocolo") or "N/A"
                
                # Atualizar status do atendimento para "Registrado"
                if codigo_inicial in atendimentos_pendentes:
                    atendimentos_pendentes[codigo_inicial]["status"] = "Registrado"
                    atendimentos_pendentes[codigo_inicial]["codigo_interno"] = codigo_interno
                    atendimentos_pendentes[codigo_inicial]["data_registro"] = datetime.now().isoformat()
                    atendimentos_pendentes[codigo_inicial]["resposta_correios"] = resultado
                
                print(f"Atendimento registrado com sucesso. Código interno: {codigo_interno}")
            except ValueError as e:
                # Resposta não é JSON válido
                print(f"Resposta não é JSON válido: {response.text}")
                if codigo_inicial in atendimentos_pendentes:
                    atendimentos_pendentes[codigo_inicial]["status"] = "Erro"
                    atendimentos_pendentes[codigo_inicial]["erro"] = f"Resposta inválida: {response.text}"
        else:
            # Tratar erros HTTP
            erro_msg = f"Erro HTTP {response.status_code}: {response.text}"
            print(erro_msg)
            if codigo_inicial in atendimentos_pendentes:
                atendimentos_pendentes[codigo_inicial]["status"] = "Erro"
                atendimentos_pendentes[codigo_inicial]["erro"] = erro_msg
            raise Exception(erro_msg)
        
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com o API dos Correios: {e}")
        if codigo_inicial in atendimentos_pendentes:
            atendimentos_pendentes[codigo_inicial]["status"] = "Erro"
            atendimentos_pendentes[codigo_inicial]["erro"] = f"Erro de conexão: {str(e)}"
    except Exception as e:
        print(f"Erro no processamento assíncrono: {e}")
        if codigo_inicial in atendimentos_pendentes:
            atendimentos_pendentes[codigo_inicial]["status"] = "Erro"
            atendimentos_pendentes[codigo_inicial]["erro"] = str(e)

@boletos_bp.route("/boletos/gerar-codigo-inicial", methods=["POST"])
def gerar_codigo_inicial_endpoint():
    """Gera e retorna um código inicial dos Correios."""
    try:
        codigo_inicial = gerar_codigo_inicial()
        
        # Armazenar o código inicial (em um ambiente real, seria em um banco de dados)
        codigos_iniciais[codigo_inicial] = {
            "codigo": codigo_inicial,
            "data_geracao": datetime.now().isoformat(),
            "usado": False
        }
        
        return jsonify({
            "sucesso": True,
            "codigo_inicial": codigo_inicial,
            "mensagem": "Código inicial gerado com sucesso"
        }), 200
        
    except Exception as e:
        print(f"Erro ao gerar código inicial: {e}")
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro interno do servidor"
        }), 500

@boletos_bp.route("/boletos/consultar-por-barras", methods=["POST"])
def consultar_boleto_por_codigo_barras():
    """Consulta um boleto pelo código de barras fornecido."""
    try:
        # Obter o código de barras da requisição
        data = request.json
        codigo_barras = data.get("codigo_barras", "").strip()
        
        if not codigo_barras:
            return jsonify({
                "sucesso": False,
                "mensagem": "Código de barras é obrigatório"
            }), 400
        
        # Carregar os dados dos boletos
        df_boletos = carregar_dados_boletos()
        
        if df_boletos.empty:
            return jsonify({
                "sucesso": False,
                "mensagem": "Base de dados de boletos não disponível"
            }), 500
        
        # Buscar o boleto pelo código de barras
        boleto_encontrado = df_boletos[df_boletos["codigo_barras"] == codigo_barras]
        
        if boleto_encontrado.empty:
            return jsonify({
                "sucesso": False,
                "mensagem": f"Boleto com código de barras não encontrado"
            }), 404
        
        # Converter o resultado para dicionário
        boleto_info = boleto_encontrado.iloc[0].to_dict()
        
        # Formatar os dados para retorno
        resultado = {
            "sucesso": True,
            "boleto": {
                "codigo_boleto": boleto_info["codigo_boleto"],
                "codigo_barras": boleto_info["codigo_barras"],
                "nome_devedor": boleto_info["nome_devedor"],
                "cpf_devedor": boleto_info["cpf_devedor"],
                "identificacao_cliente": boleto_info["identificacao_cliente"],
                "valor": float(boleto_info["valor"]),
                "data_vencimento": boleto_info["data_vencimento"],
                "status": boleto_info["status"],
                "descricao": boleto_info["descricao"],
                "codigo_correios": boleto_info["codigo_correios"]
            }
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro na consulta do boleto por código de barras: {e}")
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro interno do servidor"
        }), 500

@boletos_bp.route("/boletos/iniciar-atendimento", methods=["POST"])
def iniciar_atendimento():
    """Inicia o atendimento, gerando o JSON específico e processando de forma assíncrona."""
    try:
        # Obter os dados do atendimento
        data = request.json
        codigo_inicial = data.get("codigo_inicial", "")
        codigo_barras = data.get("codigo_barras", "")
        
        if not codigo_inicial or not codigo_barras:
            return jsonify({
                "sucesso": False,
                "mensagem": "Código inicial e código de barras são obrigatórios"
            }), 400
        
        # Verificar se o código inicial é válido
        if codigo_inicial not in codigos_iniciais:
            return jsonify({
                "sucesso": False,
                "mensagem": "Código inicial inválido"
            }), 400
        
        # Buscar o boleto pelo código de barras
        df_boletos = carregar_dados_boletos()
        boleto_encontrado = df_boletos[df_boletos["codigo_barras"] == codigo_barras]
        
        if boleto_encontrado.empty:
            return jsonify({
                "sucesso": False,
                "mensagem": "Boleto não encontrado"
            }), 404
        
        boleto_info = boleto_encontrado.iloc[0].to_dict()
        
        # Gerar o JSON específico conforme os requisitos da API dos Correios
        json_atendimento = {
            "codigoCorreios": codigo_inicial,
            "valorServico": str(int(float(boleto_info["valor"]) * 100)),  # Converter para centavos como string
            "numeroIdentificacaoCliente": boleto_info["cpf_devedor"].replace(".", "").replace("-", ""),  # CPF sem formatação
            "quantidade": "1",
            "chaveCliente": f"ASL-{boleto_info["codigo_boleto"]}",  # Formato conforme exemplo
            "textoTicket": "Texto adicional no ticket"
        }
        
        # Criar registro de atendimento pendente
        atendimentos_pendentes[codigo_inicial] = {
            "json_enviado": json_atendimento,
            "status": "Pendente",
            "data_inicio": datetime.now().isoformat(),
            "boleto_info": boleto_info
        }
        
        # Marcar código inicial como usado
        codigos_iniciais[codigo_inicial]["usado"] = True
        
        # Iniciar processamento assíncrono
        thread = threading.Thread(
            target=processar_atendimento_assincrono,
            args=(json_atendimento, codigo_inicial)
        )
        thread.daemon = True
        thread.start()
        
        # Retornar resposta imediata com status pendente
        resultado = {
            "sucesso": True,
            "status": "Pendente",
            "codigo_inicial": codigo_inicial,
            "mensagem": "Atendimento iniciado. Processamento em andamento...",
            "json_gerado": json_atendimento
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro ao iniciar atendimento: {e}")
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro interno do servidor"
        }), 500

@boletos_bp.route("/boletos/status-atendimento/<codigo_inicial>", methods=["GET"])
def consultar_status_atendimento(codigo_inicial):
    """Consulta o status de um atendimento pelo código inicial."""
    try:
        if codigo_inicial not in atendimentos_pendentes:
            return jsonify({
                "sucesso": False,
                "mensagem": "Atendimento não encontrado"
            }), 404
        
        atendimento = atendimentos_pendentes[codigo_inicial]
        
        resultado = {
            "sucesso": True,
            "codigo_inicial": codigo_inicial,
            "status": atendimento.get("status", "Desconhecido"),
            "data_inicio": atendimento.get("data_inicio"),
            "data_registro": atendimento.get("data_registro"),
            "data_liquidacao": atendimento.get("data_liquidacao"),
            "codigo_interno": atendimento.get("codigo_interno"),
            "erro": atendimento.get("erro")
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro ao consultar status do atendimento: {e}")
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro interno do servidor"
        }), 500

# Manter endpoint antigo para compatibilidade
@boletos_bp.route("/confirmarAtendimento", methods=["POST"])
def confirmar_atendimento():
    """Endpoint para confirmação de atendimento pelos Correios conforme item 8.1 da documentação."""
    try:
        # Obter os dados da requisição
        data = request.json
        numero_protocolo = data.get("numeroProtocolo", "")
        codigo_confirmacao = data.get("codigoConfirmacao", "")
        
        # Validar campos obrigatórios
        if not numero_protocolo:
            return jsonify({
                "codigo": ""
            }), 400
        
        if not codigo_confirmacao:
            return jsonify({
                "codigo": ""
            }), 400
        
        # Buscar o atendimento pelo protocolo
        atendimento_encontrado = None
        for codigo_inicial, atendimento in atendimentos_pendentes.items():
            if atendimento.get("protocolo") == numero_protocolo:
                atendimento_encontrado = atendimento
                break
        
        if not atendimento_encontrado:
            return jsonify({
                "codigo": ""
            }), 404
        
        # Atualizar o status do atendimento
        if codigo_confirmacao == "00":
            atendimento_encontrado["status"] = "Confirmado"
        else:
            atendimento_encontrado["status"] = "Erro na Confirmação"
            atendimento_encontrado["erro_confirmacao"] = codigo_confirmacao
        
        return jsonify({
            "codigo": "00"
        }), 200
        
    except Exception as e:
        print(f"Erro na confirmação do atendimento: {e}")
        return jsonify({
            "codigo": ""
        }), 500
