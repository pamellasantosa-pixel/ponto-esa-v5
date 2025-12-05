"""
Sistema de Geocodificação Reversa para Ponto ExSA v5.0
Converte coordenadas GPS em endereços legíveis
"""

import streamlit as st
import requests
from typing import Optional, Dict
import logging
import time

logger = logging.getLogger(__name__)

# Cache para endereços (evitar múltiplas requisições para mesmas coordenadas)
# Usa st.cache_data para persistir durante a sessão


@st.cache_data(ttl=3600)  # Cache de 1 hora
def coordenadas_para_endereco(latitude: float, longitude: float) -> Optional[str]:
    """
    Converte coordenadas GPS em endereço usando Nominatim (OpenStreetMap)
    
    Args:
        latitude: Latitude em graus decimais
        longitude: Longitude em graus decimais
    
    Returns:
        Endereço formatado ou None se falhar
    """
    if not latitude or not longitude:
        return None
    
    try:
        # API Nominatim (gratuita, requer User-Agent)
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "addressdetails": 1,
            "zoom": 18  # Nível de detalhe (18 = máximo)
        }
        
        headers = {
            "User-Agent": "PontoExSA/5.0 (Sistema de Controle de Ponto)"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrair partes do endereço
            address = data.get("address", {})
            
            # Montar endereço formatado
            partes = []
            
            # Rua e número
            if address.get("road"):
                rua = address["road"]
                if address.get("house_number"):
                    rua += f", {address['house_number']}"
                partes.append(rua)
            
            # Bairro
            bairro = address.get("suburb") or address.get("neighbourhood") or address.get("quarter")
            if bairro:
                partes.append(bairro)
            
            # Cidade
            cidade = address.get("city") or address.get("town") or address.get("municipality")
            if cidade:
                partes.append(cidade)
            
            # Estado (abreviado)
            estado = address.get("state")
            if estado:
                # Abreviar estados do Brasil
                estados_br = {
                    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
                    "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF", 
                    "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
                    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
                    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE",
                    "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
                    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
                    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
                }
                estado_abrev = estados_br.get(estado, estado[:2].upper())
                partes.append(estado_abrev)
            
            if partes:
                return " - ".join(partes)
            else:
                # Fallback para o display_name completo
                return data.get("display_name", "").split(",")[0:3]
        
        return None
        
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout ao buscar endereço para {latitude}, {longitude}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar endereço: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado na geocodificação: {e}")
        return None


def formatar_localizacao_gestor(latitude: float, longitude: float, 
                                 localizacao_original: str = None) -> Dict[str, str]:
    """
    Formata a localização para exibição ao gestor
    
    Returns:
        Dict com 'endereco', 'coordenadas' e 'maps_url'
    """
    resultado = {
        "endereco": None,
        "coordenadas": None,
        "maps_url": None
    }
    
    if latitude and longitude:
        # Coordenadas formatadas
        resultado["coordenadas"] = f"{latitude:.6f}, {longitude:.6f}"
        
        # URL do Google Maps
        resultado["maps_url"] = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        # Tentar obter endereço
        endereco = coordenadas_para_endereco(latitude, longitude)
        if endereco:
            resultado["endereco"] = endereco
        elif localizacao_original and localizacao_original != "GPS não disponível":
            resultado["endereco"] = localizacao_original
    
    return resultado


def exibir_localizacao_registro(latitude: float, longitude: float, 
                                localizacao_original: str = None,
                                mostrar_mapa: bool = True):
    """
    Exibe a localização formatada em um componente Streamlit
    
    Args:
        latitude: Latitude
        longitude: Longitude
        localizacao_original: String de localização original
        mostrar_mapa: Se deve mostrar link para o mapa
    """
    if not latitude or not longitude:
        st.caption("📍 GPS não disponível")
        return
    
    loc = formatar_localizacao_gestor(latitude, longitude, localizacao_original)
    
    if loc["endereco"]:
        st.markdown(f"📍 **{loc['endereco']}**")
    else:
        st.markdown(f"📍 Coordenadas: {loc['coordenadas']}")
    
    if mostrar_mapa and loc["maps_url"]:
        st.markdown(f"[🗺️ Ver no Mapa]({loc['maps_url']})")


# Cache local para evitar múltiplas chamadas à API durante uma sessão
_endereco_cache = {}


def get_endereco_cached(latitude: float, longitude: float) -> Optional[str]:
    """
    Versão com cache em memória (mais rápida para múltiplos registros)
    """
    if not latitude or not longitude:
        return None
    
    # Arredondar para 5 casas decimais (~1m de precisão)
    key = f"{latitude:.5f},{longitude:.5f}"
    
    if key in _endereco_cache:
        return _endereco_cache[key]
    
    endereco = coordenadas_para_endereco(latitude, longitude)
    if endereco:
        _endereco_cache[key] = endereco
    
    return endereco


# Teste local
if __name__ == "__main__":
    # Teste com coordenadas de exemplo (Belo Horizonte)
    lat = -19.922944
    lng = -43.932058
    
    print(f"Coordenadas: {lat}, {lng}")
    
    endereco = coordenadas_para_endereco(lat, lng)
    print(f"Endereço: {endereco}")
    
    loc = formatar_localizacao_gestor(lat, lng)
    print(f"Formatado: {loc}")
