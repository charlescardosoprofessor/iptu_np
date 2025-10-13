from flask import Blueprint, jsonify, request
import pandas as pd
import os
import requests
import threading
import time
import uuid
from datetime import datetime

boletos_bp = Blueprint('boletos', __name__)

# Variáveis globais para armazenar os dados dos boletos e códigos iniciais
dados_boletos = None
codigos_iniciais = {}  # Armazena códigos iniciais por sessão
atendimentos_pendentes = {}  # Armazena atendimentos com status pendente

# URL do API dos Correios
# URL da API dos Correios (será fornecida pelos Correios em produção)
CORREIOS_API_URL = os.getenv("CORREIOS_API_URL", "http://localhost:5001/api/v1/atendimentos/registra")

def carregar_dados_boletos():
    """Carrega os dados da planilha Excel em memória."""
    global dados_boletos
    
    if dados_boletos is None:
        try:
            # Caminho para a planilha Excel
            caminho_arquivo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'boletos_exemplo.xlsx')
            
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
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
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
        
        response = requests.post(
            CORREIOS_API_URL,
            json=dados_atendimento,
            timeout=10
        )
        
        if response.status_code == 200:
            resultado = response.json()
            
            if resultado.get('sucesso'):
                protocolo = resultado.get('protocolo_atendimento')
                
                # Atualizar status do atendimento para "Liquidado"
                if codigo_inicial in atendimentos_pendentes:
                    atendimentos_pendentes[codigo_inicial]['status'] = 'Liquidado'
                    atendimentos_pendentes[codigo_inicial]['protocolo'] = protocolo
                    atendimentos_pendentes[codigo_inicial]['data_liquidacao'] = datetime.now().isoformat()
                    atendimentos_pendentes[codigo_inicial]['resposta_correios'] = resultado
                
                print(f"Atendimento processado com sucesso. Protocolo: {protocolo}")
            else:
                raise Exception(f"Erro retornado pelo simulador: {resultado.get('mensagem')}")
        else:
            raise Exception(f"Erro HTTP {response.status_code}: {response.text}")
        
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com o API dos Correios: {e}")
        if codigo_inicial in atendimentos_pendentes:
            atendimentos_pendentes[codigo_inicial]['status'] = 'Erro'
            atendimentos_pendentes[codigo_inicial]['erro'] = f"Erro de conexão: {str(e)}"
    except Exception as e:
        print(f"Erro no processamento assíncrono: {e}")
        if codigo_inicial in atendimentos_pendentes:
            atendimentos_pendentes[codigo_inicial]['status'] = 'Erro'
            atendimentos_pendentes[codigo_inicial]['erro'] = str(e)

@boletos_bp.route('/boletos/gerar-codigo-inicial', methods=['POST'])
def gerar_codigo_inicial_endpoint():
    """Gera e retorna um código inicial dos Correios."""
    try:
        codigo_inicial = gerar_codigo_inicial()
        
        # Armazenar o código inicial (em um ambiente real, seria em um banco de dados)
        codigos_iniciais[codigo_inicial] = {
            'codigo': codigo_inicial,
            'data_geracao': datetime.now().isoformat(),
            'usado': False
        }
        
        return jsonify({
            'sucesso': True,
            'codigo_inicial': codigo_inicial,
            'mensagem': 'Código inicial gerado com sucesso'
        }), 200
        
    except Exception as e:
        print(f"Erro ao gerar código inicial: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }), 500

@boletos_bp.route('/boletos/consultar-por-barras', methods=['POST'])
def consultar_boleto_por_codigo_barras():
    """Consulta um boleto pelo código de barras fornecido."""
    try:
        # Obter o código de barras da requisição
        data = request.json
        codigo_barras = data.get('codigo_barras', '').strip()
        
        if not codigo_barras:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Código de barras é obrigatório'
            }), 400
        
        # Carregar os dados dos boletos
        df_boletos = carregar_dados_boletos()
        
        if df_boletos.empty:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Base de dados de boletos não disponível'
            }), 500
        
        # Buscar o boleto pelo código de barras
        boleto_encontrado = df_boletos[df_boletos['codigo_barras'] == codigo_barras]
        
        if boleto_encontrado.empty:
            return jsonify({
                'sucesso': False,
                'mensagem': f'Boleto com código de barras não encontrado'
            }), 404
        
        # Converter o resultado para dicionário
        boleto_info = boleto_encontrado.iloc[0].to_dict()
        
        # Formatar os dados para retorno
        resultado = {
            'sucesso': True,
            'boleto': {
                'codigo_boleto': boleto_info['codigo_boleto'],
                'codigo_barras': boleto_info['codigo_barras'],
                'nome_devedor': boleto_info['nome_devedor'],
                'cpf_devedor': boleto_info['cpf_devedor'],
                'identificacao_cliente': boleto_info['identificacao_cliente'],
                'valor': float(boleto_info['valor']),
                'data_vencimento': boleto_info['data_vencimento'],
                'status': boleto_info['status'],
                'descricao': boleto_info['descricao'],
                'codigo_correios': boleto_info['codigo_correios']
            }
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro na consulta do boleto por código de barras: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }), 500

@boletos_bp.route('/boletos/iniciar-atendimento', methods=['POST'])
def iniciar_atendimento():
    """Inicia o atendimento, gerando o JSON específico e processando de forma assíncrona."""
    try:
        # Obter os dados do atendimento
        data = request.json
        codigo_inicial = data.get('codigo_inicial', '')
        codigo_barras = data.get('codigo_barras', '')
        
        if not codigo_inicial or not codigo_barras:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Código inicial e código de barras são obrigatórios'
            }), 400
        
        # Verificar se o código inicial é válido
        if codigo_inicial not in codigos_iniciais:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Código inicial inválido'
            }), 400
        
        # Buscar o boleto pelo código de barras
        df_boletos = carregar_dados_boletos()
        boleto_encontrado = df_boletos[df_boletos['codigo_barras'] == codigo_barras]
        
        if boleto_encontrado.empty:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Boleto não encontrado'
            }), 404
        
        boleto_info = boleto_encontrado.iloc[0].to_dict()
        
        # Gerar o JSON específico conforme os requisitos
        json_atendimento = {
            'chaveInicialCorreios': codigo_inicial,
            'cpfPessoa': boleto_info['cpf_devedor'],
            'identificacaoCliente': boleto_info['identificacao_cliente'],
            'codigoReferenciaBoleto': boleto_info['codigo_boleto'],
            'mensagemPadrao': f"Recebemos esse valor {boleto_info['nome_devedor']} ref. ao iptu 2025",
            'valor': converter_valor_para_centavos(float(boleto_info['valor'])),
            'quantidade': '1x1'
        }
        
        # Criar registro de atendimento pendente
        atendimentos_pendentes[codigo_inicial] = {
            'json_enviado': json_atendimento,
            'status': 'Pendente',
            'data_inicio': datetime.now().isoformat(),
            'boleto_info': boleto_info
        }
        
        # Marcar código inicial como usado
        codigos_iniciais[codigo_inicial]['usado'] = True
        
        # Iniciar processamento assíncrono
        thread = threading.Thread(
            target=processar_atendimento_assincrono,
            args=(json_atendimento, codigo_inicial)
        )
        thread.daemon = True
        thread.start()
        
        # Retornar resposta imediata com status pendente
        resultado = {
            'sucesso': True,
            'status': 'Pendente',
            'codigo_inicial': codigo_inicial,
            'mensagem': 'Atendimento iniciado. Processamento em andamento...',
            'json_gerado': json_atendimento
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro ao iniciar atendimento: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }), 500

@boletos_bp.route('/boletos/status-atendimento/<codigo_inicial>', methods=['GET'])
def consultar_status_atendimento(codigo_inicial):
    """Consulta o status de um atendimento pelo código inicial."""
    try:
        if codigo_inicial not in atendimentos_pendentes:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Atendimento não encontrado'
            }), 404
        
        atendimento = atendimentos_pendentes[codigo_inicial]
        
        resultado = {
            'sucesso': True,
            'codigo_inicial': codigo_inicial,
            'status': atendimento['status'],
            'data_inicio': atendimento['data_inicio']
        }
        
        # Adicionar informações específicas baseadas no status
        if atendimento['status'] == 'Liquidado':
            resultado['protocolo'] = atendimento.get('protocolo')
            resultado['data_liquidacao'] = atendimento.get('data_liquidacao')
            resultado['resposta_correios'] = atendimento.get('resposta_correios')
        elif atendimento['status'] == 'Erro':
            resultado['erro'] = atendimento.get('erro')
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro ao consultar status do atendimento: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }), 500

@boletos_bp.route('/boletos/status', methods=['GET'])
def status_sistema():
    """Retorna o status do sistema e informações sobre os dados carregados."""
    try:
        df_boletos = carregar_dados_boletos()
        
        status = {
            'sistema': 'STER CONTRATANTE',
            'status': 'Operacional',
            'total_boletos': len(df_boletos) if not df_boletos.empty else 0,
            'codigos_iniciais_gerados': len(codigos_iniciais),
            'atendimentos_pendentes': len([a for a in atendimentos_pendentes.values() if a['status'] == 'Pendente']),
            'atendimentos_liquidados': len([a for a in atendimentos_pendentes.values() if a['status'] == 'Liquidado']),
            'correios_api_url': CORREIOS_API_URL,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        print(f"Erro ao obter status do sistema: {e}")
        return jsonify({
            'sistema': 'STER CONTRATANTE',
            'status': 'Erro',
            'mensagem': 'Erro interno do servidor'
        }), 500

# Manter endpoint antigo para compatibilidade
@boletos_bp.route('/confirmarAtendimento', methods=['POST'])
def confirmar_atendimento():
    """Endpoint para confirmação de atendimento pelos Correios conforme item 8.1 da documentação."""
    try:
        # Obter os dados da requisição
        data = request.json
        numero_protocolo = data.get('numeroProtocolo', '')
        codigo_confirmacao = data.get('codigoConfirmacao', '')
        
        # Validar campos obrigatórios
        if not numero_protocolo:
            return jsonify({
                'codigo': ''
            }), 400
        
        if not codigo_confirmacao:
            return jsonify({
                'codigo': ''
            }), 400
        
        # Buscar o atendimento pelo protocolo
        atendimento_encontrado = None
        codigo_inicial_encontrado = None
        
        for codigo_inicial, atendimento in atendimentos_pendentes.items():
            if atendimento.get('protocolo') == numero_protocolo:
                atendimento_encontrado = atendimento
                codigo_inicial_encontrado = codigo_inicial
                break
        
        if not atendimento_encontrado:
            print(f"Protocolo {numero_protocolo} não encontrado nos atendimentos")
            return jsonify({
                'codigo': ''
            }), 400
        
        # Processar a confirmação
        if codigo_confirmacao == "00":
            # Confirmação positiva
            atendimentos_pendentes[codigo_inicial_encontrado]['status'] = 'Confirmado'
            atendimentos_pendentes[codigo_inicial_encontrado]['data_confirmacao'] = datetime.now().isoformat()
            atendimentos_pendentes[codigo_inicial_encontrado]['codigo_confirmacao'] = codigo_confirmacao
            
            print(f"Atendimento {numero_protocolo} confirmado com sucesso")
            
            # Retornar código de sucesso
            return jsonify({
                'codigo': f'CONF_{numero_protocolo}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            }), 200
            
        elif codigo_confirmacao == "99":
            # Confirmação negativa
            atendimentos_pendentes[codigo_inicial_encontrado]['status'] = 'Não Confirmado'
            atendimentos_pendentes[codigo_inicial_encontrado]['data_confirmacao'] = datetime.now().isoformat()
            atendimentos_pendentes[codigo_inicial_encontrado]['codigo_confirmacao'] = codigo_confirmacao
            
            print(f"Atendimento {numero_protocolo} não confirmado")
            
            # Retornar código de sucesso (mesmo para confirmação negativa)
            return jsonify({
                'codigo': f'NCONF_{numero_protocolo}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            }), 200
        else:
            # Código de confirmação inválido
            print(f"Código de confirmação inválido: {codigo_confirmacao}")
            return jsonify({
                'codigo': ''
            }), 400
        
    except Exception as e:
        print(f"Erro na confirmação do atendimento: {e}")
        return jsonify({
            'codigo': ''
        }), 400

@boletos_bp.route('/boletos/consultar', methods=['POST'])
def consultar_boleto():
    """Consulta um boleto pelo código fornecido (compatibilidade)."""
    try:
        # Obter o código do boleto da requisição
        data = request.json
        codigo_boleto = data.get('codigo_boleto', '').strip()
        
        if not codigo_boleto:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Código do boleto é obrigatório'
            }), 400
        
        # Carregar os dados dos boletos
        df_boletos = carregar_dados_boletos()
        
        if df_boletos.empty:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Base de dados de boletos não disponível'
            }), 500
        
        # Buscar o boleto pelo código
        boleto_encontrado = df_boletos[df_boletos['codigo_boleto'].str.upper() == codigo_boleto.upper()]
        
        if boleto_encontrado.empty:
            return jsonify({
                'sucesso': False,
                'mensagem': f'Boleto com código {codigo_boleto} não encontrado'
            }), 404
        
        # Converter o resultado para dicionário
        boleto_info = boleto_encontrado.iloc[0].to_dict()
        
        # Formatar os dados para retorno
        resultado = {
            'sucesso': True,
            'boleto': {
                'codigo_boleto': boleto_info['codigo_boleto'],
                'codigo_barras': boleto_info.get('codigo_barras', ''),
                'nome_devedor': boleto_info['nome_devedor'],
                'cpf_devedor': boleto_info.get('cpf_devedor', ''),
                'identificacao_cliente': boleto_info.get('identificacao_cliente', boleto_info['nome_devedor']),
                'valor': float(boleto_info['valor']),
                'data_vencimento': boleto_info['data_vencimento'],
                'status': boleto_info['status'],
                'descricao': boleto_info['descricao'],
                'codigo_correios': boleto_info['codigo_correios']
            }
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"Erro na consulta do boleto: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }), 500
