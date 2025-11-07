# 📱 Notificações Push Mobile - Documentação Técnica

## 📋 Visão Geral

Este documento descreve a estrutura e endpoints necessários para integração de notificações push mobile no Sistema de Ponto ESA v5.

---

## 🏗️ Arquitetura Proposta

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   App Mobile    │────────▶│  Backend API     │────────▶│  Firebase FCM   │
│   (Flutter/RN)  │◀────────│  (Python/Flask)  │◀────────│  Push Service   │
└─────────────────┘         └──────────────────┘         └─────────────────┘
       │                            │
       │                            │
       │                    ┌───────▼─────────┐
       └───────────────────▶│   PostgreSQL    │
                            │   Database      │
                            └─────────────────┘
```

---

## 🗄️ Estrutura de Banco de Dados

### Tabela: `dispositivos_mobile`

```sql
CREATE TABLE dispositivos_mobile (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(255) NOT NULL,
    device_token VARCHAR(512) NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL, -- 'ios' ou 'android'
    modelo_dispositivo VARCHAR(100),
    versao_app VARCHAR(20),
    ativo BOOLEAN DEFAULT TRUE,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_ultima_atividade TIMESTAMP,
    FOREIGN KEY (usuario) REFERENCES usuarios(usuario)
);

CREATE INDEX idx_dispositivos_usuario ON dispositivos_mobile(usuario);
CREATE INDEX idx_dispositivos_ativo ON dispositivos_mobile(ativo);
```

### Tabela: `notificacoes_push`

```sql
CREATE TABLE notificacoes_push (
    id SERIAL PRIMARY KEY,
    usuario_destino VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT NOT NULL,
    dados_extra JSONB,
    enviada BOOLEAN DEFAULT FALSE,
    data_envio TIMESTAMP,
    lida BOOLEAN DEFAULT FALSE,
    data_leitura TIMESTAMP,
    erro TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_destino) REFERENCES usuarios(usuario)
);

CREATE INDEX idx_notif_usuario ON notificacoes_push(usuario_destino);
CREATE INDEX idx_notif_enviada ON notificacoes_push(enviada);
CREATE INDEX idx_notif_lida ON notificacoes_push(lida);
```

---

## 📡 Endpoints da API

### 1. Registrar Dispositivo

**POST** `/api/mobile/register-device`

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "usuario": "joao.silva",
  "device_token": "fcm_token_aqui...",
  "platform": "android",
  "modelo_dispositivo": "Samsung Galaxy S21",
  "versao_app": "1.0.0"
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Dispositivo registrado com sucesso",
  "device_id": 123
}
```

---

### 2. Atualizar Token do Dispositivo

**PUT** `/api/mobile/update-token`

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "device_id": 123,
  "device_token": "novo_fcm_token..."
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Token atualizado com sucesso"
}
```

---

### 3. Desativar Dispositivo

**DELETE** `/api/mobile/device/{device_id}`

**Headers:**
```
Authorization: Bearer {token}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Dispositivo desativado"
}
```

---

### 4. Listar Notificações

**GET** `/api/mobile/notifications?usuario={usuario}&limit=50&offset=0`

**Headers:**
```
Authorization: Bearer {token}
```

**Response 200:**
```json
{
  "success": true,
  "notifications": [
    {
      "id": 456,
      "tipo": "hora_extra_aprovada",
      "titulo": "✅ Hora Extra Aprovada",
      "mensagem": "Sua solicitação foi aprovada por Maria Silva",
      "dados_extra": {
        "hora_extra_id": 789
      },
      "lida": false,
      "data_criacao": "2025-11-07T14:30:00"
    }
  ],
  "total": 10,
  "nao_lidas": 3
}
```

---

### 5. Marcar Notificação como Lida

**PUT** `/api/mobile/notifications/{notification_id}/read`

**Headers:**
```
Authorization: Bearer {token}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Notificação marcada como lida"
}
```

---

## 🔥 Integração com Firebase Cloud Messaging (FCM)

### Configuração

```python
# config/firebase_config.py

import firebase_admin
from firebase_admin import credentials, messaging

# Inicializar Firebase Admin SDK
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

def enviar_push_notification(device_token, titulo, mensagem, dados_extra=None):
    """
    Envia notificação push via Firebase FCM
    
    Args:
        device_token (str): Token do dispositivo
        titulo (str): Título da notificação
        mensagem (str): Corpo da mensagem
        dados_extra (dict): Dados adicionais (opcional)
    
    Returns:
        dict: Resultado do envio
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=mensagem,
            ),
            data=dados_extra or {},
            token=device_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='horas_extras'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        response = messaging.send(message)
        return {'success': True, 'message_id': response}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

## 📨 Tipos de Notificações

### 1. Solicitação de Hora Extra

```json
{
  "tipo": "hora_extra_solicitada",
  "titulo": "🕐 Nova Solicitação de Hora Extra",
  "mensagem": "João Silva solicitou hora extra. Justificativa: Finalizar relatório urgente",
  "dados_extra": {
    "hora_extra_id": 123,
    "usuario_solicitante": "joao.silva",
    "acao_requerida": "aprovar_rejeitar"
  }
}
```

### 2. Hora Extra Aprovada

```json
{
  "tipo": "hora_extra_aprovada",
  "titulo": "✅ Hora Extra Aprovada",
  "mensagem": "Sua solicitação foi aprovada por Maria Silva. O contador está rodando!",
  "dados_extra": {
    "hora_extra_id": 123,
    "aprovador": "maria.silva"
  }
}
```

### 3. Hora Extra Rejeitada

```json
{
  "tipo": "hora_extra_rejeitada",
  "titulo": "❌ Hora Extra Rejeitada",
  "mensagem": "Sua solicitação foi rejeitada por Maria Silva",
  "dados_extra": {
    "hora_extra_id": 123,
    "aprovador": "maria.silva",
    "motivo": "Sem justificativa suficiente"
  }
}
```

### 4. Lembrete de Hora Extra em Andamento

```json
{
  "tipo": "hora_extra_lembrete",
  "titulo": "⏰ Hora Extra em Andamento",
  "mensagem": "Você está em hora extra há 2h. Não esqueça de encerrar!",
  "dados_extra": {
    "hora_extra_id": 123,
    "tempo_decorrido_minutos": 120
  }
}
```

### 5. Limite de Horas Extras Atingido

```json
{
  "tipo": "limite_hora_extra",
  "titulo": "⚠️ Limite de Horas Extras Próximo",
  "mensagem": "Você atingiu 8h de 10h semanais permitidas",
  "dados_extra": {
    "horas_semana": 8.0,
    "limite_semana": 10.0
  }
}
```

---

## 🔒 Autenticação

### JWT Token

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "sua_chave_secreta_aqui"

def gerar_token(usuario):
    """Gera token JWT para autenticação"""
    payload = {
        'usuario': usuario,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def validar_token(token):
    """Valida token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return {'valido': True, 'usuario': payload['usuario']}
    except jwt.ExpiredSignatureError:
        return {'valido': False, 'erro': 'Token expirado'}
    except jwt.InvalidTokenError:
        return {'valido': False, 'erro': 'Token inválido'}
```

---

## 🔄 Fluxo Completo de Notificação

```
1. EVENTO OCORRE NO SISTEMA
   (Ex: Gestor aprova hora extra)
   ↓
2. CRIAR REGISTRO EM notificacoes_push
   INSERT INTO notificacoes_push (...)
   ↓
3. BUSCAR TOKENS DOS DISPOSITIVOS DO USUÁRIO
   SELECT device_token FROM dispositivos_mobile 
   WHERE usuario = ? AND ativo = TRUE
   ↓
4. ENVIAR PARA FIREBASE FCM
   firebase_admin.messaging.send(message)
   ↓
5. ATUALIZAR STATUS
   UPDATE notificacoes_push SET enviada = TRUE, data_envio = NOW()
   ↓
6. DISPOSITIVO RECEBE NOTIFICAÇÃO
   App mostra notificação na barra de status
   ↓
7. USUÁRIO CLICA NA NOTIFICAÇÃO
   App abre tela específica (deep link)
   ↓
8. MARCAR COMO LIDA
   PUT /api/mobile/notifications/{id}/read
```

---

## 📱 Configuração no App Mobile

### Flutter (Android)

**pubspec.yaml:**
```yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_messaging: ^14.7.6
```

**main.dart:**
```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  print("Notificação em background: ${message.notification?.title}");
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  runApp(MyApp());
}

class NotificationService {
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  
  Future<String?> getToken() async {
    return await _messaging.getToken();
  }
  
  Future<void> requestPermission() async {
    NotificationSettings settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    print('Permissão: ${settings.authorizationStatus}');
  }
  
  void listenToNotifications() {
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('Notificação recebida: ${message.notification?.title}');
      // Mostrar notificação local ou atualizar UI
    });
    
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      print('App aberto por notificação');
      // Navegar para tela específica
      _handleNotificationTap(message.data);
    });
  }
  
  void _handleNotificationTap(Map<String, dynamic> data) {
    String tipo = data['tipo'];
    
    switch (tipo) {
      case 'hora_extra_aprovada':
        // Navegar para tela de horas extras
        Navigator.pushNamed(context, '/horas-extras');
        break;
      case 'hora_extra_solicitada':
        // Navegar para tela de aprovações
        Navigator.pushNamed(context, '/aprovar-horas-extras');
        break;
    }
  }
}
```

---

## 🧪 Testes

### Teste de Envio de Notificação

```python
# test_push_notifications.py

import requests

def testar_envio_notificacao():
    url = "http://localhost:5000/api/mobile/send-test-notification"
    headers = {"Authorization": "Bearer seu_token_aqui"}
    data = {
        "usuario": "joao.silva",
        "titulo": "Teste de Notificação",
        "mensagem": "Esta é uma notificação de teste"
    }
    
    response = requests.post(url, json=data, headers=headers)
    print(response.json())

if __name__ == "__main__":
    testar_envio_notificacao()
```

---

## 📊 Métricas e Monitoramento

### Queries Úteis

```sql
-- Total de notificações enviadas por tipo
SELECT tipo, COUNT(*) as total
FROM notificacoes_push
WHERE enviada = TRUE
GROUP BY tipo
ORDER BY total DESC;

-- Taxa de leitura de notificações
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN lida THEN 1 ELSE 0 END) as lidas,
    ROUND(100.0 * SUM(CASE WHEN lida THEN 1 ELSE 0 END) / COUNT(*), 2) as taxa_leitura
FROM notificacoes_push
WHERE enviada = TRUE;

-- Dispositivos ativos por plataforma
SELECT platform, COUNT(*) as total
FROM dispositivos_mobile
WHERE ativo = TRUE
GROUP BY platform;

-- Usuários com mais notificações não lidas
SELECT usuario_destino, COUNT(*) as nao_lidas
FROM notificacoes_push
WHERE lida = FALSE
GROUP BY usuario_destino
ORDER BY nao_lidas DESC
LIMIT 10;
```

---

## ⚠️ Considerações de Segurança

1. **Validação de Tokens:** Sempre validar JWT antes de processar requisições
2. **Rate Limiting:** Limitar número de requisições por usuário/IP
3. **Criptografia:** Usar HTTPS para todas as comunicações
4. **Dados Sensíveis:** Não enviar informações confidenciais nas notificações
5. **Expiração de Tokens:** Implementar renovação automática de tokens FCM
6. **Logs:** Registrar todas as tentativas de envio e erros

---

## 🚀 Implementação Futura

### Próximos Passos

1. **Fase 1:** Criar endpoints da API REST
2. **Fase 2:** Integrar Firebase FCM
3. **Fase 3:** Desenvolver app mobile (Flutter/React Native)
4. **Fase 4:** Implementar deep links
5. **Fase 5:** Adicionar notificações agendadas
6. **Fase 6:** Implementar analytics de notificações

### Recursos Adicionais

- **Notificações Agendadas:** Lembretes automáticos
- **Notificações em Grupo:** Agrupar múltiplas notificações
- **Rich Notifications:** Imagens, ações, botões
- **Quiet Hours:** Respeitar horário de silêncio do usuário

---

## 📚 Referências

- [Firebase Cloud Messaging - Documentação](https://firebase.google.com/docs/cloud-messaging)
- [Flutter Firebase Messaging](https://firebase.flutter.dev/docs/messaging/overview)
- [React Native Push Notifications](https://reactnative.dev/docs/pushnotificationios)
- [JWT Authentication](https://jwt.io/introduction)

---

**Última Atualização:** 07/11/2025  
**Versão:** 1.0  
**Autor:** Sistema Ponto ESA v5
