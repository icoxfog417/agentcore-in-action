# AWS Bedrock AgentCoreによるOAuth統合の実践ガイド

## 目次

1. [概要](#概要)
2. [リポジトリの特徴](#リポジトリの特徴)
3. [主要プロジェクト](#主要プロジェクト)
4. [アーキテクチャコンセプト](#アーキテクチャコンセプト)
5. [技術スタック](#技術スタック)
6. [ユースケースと実用例](#ユースケースと実用例)
7. [セットアップ要件](#セットアップ要件)
8. [開発者向けガイド](#開発者向けガイド)

---

## 概要

さて、今日はですね、**agentcore-in-action**という面白いリポジトリについてお話ししていきたいと思います。これはですね、Amazon Bedrock AgentCoreを使ったOAuth統合の実践例を集めたものなんですね。

皆さん、Jupyter Notebookって使ったことあります？あれ、段階的に学習するには本当にいいんですよね。でも実際のところ、既存のアプリケーションに統合しようとすると…これがなかなか大変なんですよ。そこでこのリポジトリの出番です！

このリポジトリが何をしてくれるかっていうと、その gap を埋めてくれるわけなんです。つまり、本番環境を意識した、実際に動かせるスクリプトベースの実装例を提供してくれるんですね。

### リポジトリの目的

じゃあ、具体的にこのリポジトリが目指しているものって何なんでしょうか？

まず一つ目がですね、**探索から統合への橋渡し**なんです。Notebookでの学習から実際の運用環境への移行って、これがスムーズにできるようになります。

それから二つ目、**再現可能なワークフロー**を実現しているんですね。`uv`という依存関係管理ツールを使っているので、リポジトリをクローンしたらすぐに実行できちゃうんです。便利ですよね。

三つ目として、**セキュリティを重視**してます。本番環境でのセキュリティって超重要じゃないですか。だから各例でしっかりとセキュリティの考慮事項を文書化しているんです。

そして最後に、**仕様主導**のアプローチを取ってます。まず仕様から設計して、テストを満たす実装を提供する、という流れですね。

---

## リポジトリの特徴

このリポジトリの特徴について、もう少し深く見ていきましょう。

### 明確性

まずは**明確性**です。各例がですね、包括的なドキュメントを備えた自己完結型のプロジェクトになってるんですよ。つまり、一つ一つの例が独立していて、分かりやすいってことですね。

### 再現性

次に**再現性**なんですが、これも重要なポイントです。

さっきも言いましたけど、`uv`による依存関係管理を使ってるので、リポジトリをクローンした後すぐに動かせるんです。しかも、エラーメッセージも明確だし、設定手順もしっかり書いてあるので、迷うことがないんですね。

### セキュリティ

**セキュリティ**についてはですね、かなり真剣に考えられています。

認証情報の管理はベストプラクティスに従っていますし、入力検証とサニタイゼーションもちゃんとやってます。レート制限やスロットリングも実装されていて、IAMの最小権限の原則も守られているんです。本番環境で使えるレベルってことですよね。

### 仕様主導開発

そして、**仕様主導開発**のアプローチを採用しているんですが、これがなかなか興味深いんです。

どういうことかというと、まず**仕様を定義**するところから始めるんですね。README.mdで期待される動作を定義します。

次に**テストを設計**します。その仕様に基づいて実行可能なテストを作成するわけです。

それから**実装**に入ります。テストを満たす最小限のコードを実装していく。

最後に**検証**です。セキュリティチェック、ドキュメント、トラブルシューティングをしっかり行います。

この流れ、とても理にかなってますよね。

---

## 主要プロジェクト

さて、それではですね、このリポジトリに含まれている主要なプロジェクトを見ていきましょう。

### 1. oauth-gateway-from-agent: エージェントからのOAuthゲートウェイ

**概要**

最初のプロジェクトはですね、「oauth-gateway-from-agent」というものです。これ、面白いんですよ。

何をするかっていうと、認証されたユーザーに代わって、サードパーティのAPIにアクセスするセキュアなMCPサーバーを構築するんですね。このプロジェクトの特徴はですね、**インバウンドOAuth認証**と**アウトバウンドOAuth認可**の両方を実装しているところなんです。

#### 主な機能

じゃあ具体的にどんな機能があるのか見ていきましょう。

まず**インバウンド認証**です。これはですね、GoogleのOAuthを通じて、Cognito経由でユーザーを認証するんですね。

これが何をしてくれるかというと、ユーザーが誰であるかを特定するわけです。いわゆる「WHO」の部分ですね。CognitoがGoogleサインインをフェデレーションして、GatewayのCUSTOM_JWT認証でJWTを検証するという流れです。

次に**アウトバウンド認可**があります。これはToken Vault経由でYouTube APIにアクセスするんですが、ここではですね、ユーザーが何にアクセスできるかを制御しているんです。つまり「WHAT」の部分ですね。

OAuth 2.0の認可コードグラント、いわゆる3レッグOAuthを使っていて、ユーザーごとにトークンを隔離して安全に保存するようになってます。

#### なぜCognitoが必要か？

ここでですね、「なんでCognitoが必要なの？」っていう疑問が出てくると思うんですよ。これ、実は重要なポイントなんです。

AgentCore Identityプロバイダーにはですね、異なる機能があるんです。ちょっと整理してみましょうか。

| プロバイダー | インバウンド（ユーザーID） | アウトバウンド（APIアクセス） |
|------------|------------------------|------------------------|
| **Google** | ❌ サポートなし | ✅ サポートあり |
| **Cognito** | ✅ サポートあり | ✅ サポートあり |

見てわかりますよね？GoogleのOAuthプロバイダーって、アウトバウンドのリソースアクセス専用なんですよ。インバウンドのユーザー認証には使えないんです。これが問題なわけです。

**じゃあどうするか？**答えはCognitoとGoogleを連携させることなんです。そうすることで、インバウンド認証にGoogleサインインを使いながら、アウトバウンドのトークン検索のためにGoogleユーザーIDを保持できるわけです。なるほどって感じですよね。

#### アーキテクチャ

```mermaid
flowchart TB
    subgraph AWS["AWS リソース"]
        subgraph Cognito["Cognito User Pool"]
            CUP["User Pool<br/>Google 連携"]
        end

        subgraph Identity["AgentCore Identity"]
            IP["インバウンドプロバイダー<br/>Cognito"]
            OP["アウトバウンドプロバイダー<br/>Google (YouTube API)"]
        end

        subgraph Gateway["AgentCore Gateway (MCP)"]
            GW["Gateway<br/>CUSTOM_JWT Authorizer"]
            TGT["Target<br/>YouTube API"]
        end

        subgraph Infra["コールバックインフラ"]
            CF["CloudFront Distribution"]
            LF["Lambda Function"]
            DB["DynamoDB<br/>セッションストレージ"]
        end
    end

    subgraph External["外部サービス"]
        G["Google OAuth"]
        YT["YouTube Data API v3"]
    end

    IP --> CUP
    CUP --> G
    OP --> G
    TGT --> YT
    CF --> LF
    LF --> DB
    CF -.-> G
    GW --> TGT
```

#### 実行フロー

```mermaid
sequenceDiagram
    participant User as main.py (Agent)
    participant Identity as AgentCore Identity
    participant Cognito as Cognito User Pool
    participant Google as Google OAuth
    participant Gateway as Gateway (MCP Server)
    participant Vault as Token Vault
    participant Callback as Callback Server
    participant YouTube as YouTube API

    Note over User,YouTube: フェーズ1: インバウンド認証（Cognito + Google連携）
    User->>Identity: @requires_access_token (openid, email, profile)
    Identity->>Cognito: Hosted UIにリダイレクト
    Cognito->>Google: Googleサインインにリダイレクト
    Google-->>User: on_auth_urlコールバック（ブラウザで開く）
    User->>Google: Googleでサインイン
    Google-->>Cognito: 認可コード
    Cognito->>Cognito: コード交換、ユーザー作成
    Cognito-->>Identity: Cognito JWT（identities クレーム含む）
    Identity-->>User: access_token（Cognito JWT）

    Note over User,YouTube: フェーズ2: MCPクライアントとしてGatewayに接続
    User->>Gateway: MCP initialize + Bearer Cognito JWT
    Gateway->>Gateway: Cognito JWT検証 ✓
    Gateway-->>User: MCP初期化完了、ツール利用可能

    Note over User,YouTube: フェーズ3: 初回ツール呼び出し → アウトバウンド認証（3LO）
    User->>Gateway: tools/call (list_channels)
    Gateway->>Vault: ユーザーXのYouTubeトークン取得
    Vault-->>Gateway: トークンなし（authorizationUrl + session_id）
    Gateway-->>User: 401 + authorizationUrl
    User->>User: (session_id → Cognito JWT) をDynamoDBに保存
    
    User->>Google: YouTubeスコープ承認（ブラウザ）
    Google-->>Callback: session_idでリダイレクト
    Callback->>Callback: DynamoDBからCognito JWT取得
    Callback->>Vault: CompleteResourceTokenAuth(session_id, userToken=JWT)
    Vault-->>Callback: ユーザーのトークン保存完了
    Callback-->>User: "認可完了！"

    Note over User,YouTube: フェーズ4: 以降の呼び出し → Vaultからトークン取得
    User->>Gateway: tools/call (list_channels)
    Gateway->>Vault: ユーザーXのYouTubeトークン取得
    Vault-->>Gateway: YouTube APIトークン ✓
    Gateway->>YouTube: GET /youtube/v3/channels
    YouTube-->>Gateway: チャンネルデータ
    Gateway-->>User: ツール結果（チャンネル）
```

#### 主要コンポーネント

それじゃあですね、この仕組みの主要なコンポーネントについて説明していきましょう。

**1. Cognito User Pool（Google連携）**

まず一つ目がCognito User Poolです。これがGoogleサインインをフェデレーションしてくれるんですね。

で、何をしてくれるかというと、`identities`クレームを含むJWTを発行してくれます。OAuthフローは認可コードを使っていて、スコープとしては`openid`、`email`、`profile`を使ってます。

**2. AgentCore Gateway（MCPサーバー）**

二つ目がAgentCore Gatewayです。これがMCPサーバーとして機能するわけですが、インバウンドではCognitoのJWTを検証してくれます。

ワークロードIDっていうのがあって、これがGatewayのアプリケーション識別子になってるんですね。アウトバウンドでは、Token Vaultからユーザーのトークンを取得するようになってます。

**3. OAuth コールバックサーバー（CloudFront + Lambda）**

三つ目が OAuth コールバックサーバーです。これはCloudFrontとLambdaで構成されてます。

CloudFront DistributionはDDoS保護を備えた公開エンドポイントとして機能します。Lambda FunctionはOAuthコールバックを処理して、セッションバインディングを完了させます。それから、DynamoDB Tableが自動クリーンアップのTTL付きでセッションデータを保存してくれるんです。

**じゃあ、なんでセッションバインディングが必要なの？**って思いますよね。

これはですね、セッションハイジャックを防止するためなんです。`session_id`と`user_jwt`のペアをDynamoDBに保存することで、OAuthフローを開始したユーザーだけが完了できるようになってるんです。セキュリティ、大事ですからね。

#### 実装例

実際のコードを見てみましょう。こんな感じで実装できるんです。

```python
from bedrock_agentcore.identity import requires_access_token
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient

@requires_access_token(
    provider_name=INBOUND_PROVIDER_NAME,
    scopes=["openid", "email", "profile"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: webbrowser.open(url),
)
def run_agent(*, access_token: str):
    """Gatewayを MCPサーバーとしてエージェントを実行。
    
    access_tokenは、以下を含むCognito JWT（Google連携）：
    - sub: Cognito ユーザーID
    - identities: [{"providerName": "Google", "userId": "<google_user_id>"}]
    """
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            GATEWAY_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    )
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(tools=tools)
        response = agent("YouTubeチャンネルをリスト表示")
        print(response)
```

ね、結構シンプルに書けるでしょう？

#### セキュリティ考慮事項

最後にですね、セキュリティについてちょっと話しておきたいんですが、このプロジェクトではかなり気を使ってます。

まず**トークン隔離**ですね。各ユーザーのGoogleトークンをToken Vaultで個別に保存してます。他のユーザーのトークンにはアクセスできないようになってるわけです。

それから**IDバインディング**。JWTの`sub`クレームに基づいてトークンを取得するようになってます。

**スコープ分離**も重要で、インバウンド（ID確認）とアウトバウンド（APIアクセス）で異なるスコープを使ってます。

**トークン非公開**の原則も守られていて、Google APIのトークンはクライアントに送信されません。

最後に**KMS暗号化**です。DynamoDBのトークンストレージはKMSで暗号化されてます。本番環境では必須ですよね、これ。


---

### 2. oauth-gateway-from-browser: ブラウザからのOAuthゲートウェイ

**概要**

さて、次は二つ目のプロジェクトです。「oauth-gateway-from-browser」っていうんですが、これも面白いですよ。

これは何をするかというと、OAuth 2.0の認可コードグラント、つまり3レッグOAuthを使って、ユーザーのYouTubeデータに基づいたパーソナライズされたメッセージでユーザーに挨拶するエージェントを構築するんです。ユーザー体験を考えたアプローチですよね。

#### 主な機能

このプロジェクトの主な機能をいくつか見ていきましょう。

まずですね、**ブラウザベースのOAuthフロー**があります。Cognito Hosted UIを通じてユーザー認証を行うんですね。

それから**デュアルOAuthフロー**というのが特徴的です。これ、二つのフローがあるんですよ。

一つ目がCognito認可コードフロー、いわゆるインバウンドですね。これでカスタムスコープを含むアクセストークンを取得します。

二つ目がYouTube OAuthフロー、つまりアウトバウンドです。API呼び出し用のYouTubeアクセストークンを取得するわけです。

**ユーザー委任アクセス**も実装されていて、エージェントがユーザーの認証情報を見ることなく外部APIにアクセスできるんです。これ、セキュリティ的に重要ですよね。

そして**セキュアなトークン管理**です。AgentCore Identityがユーザーごとのトークンバインディングを管理してくれます。

#### アーキテクチャ

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Server as OAuth2 Server<br/>(localhost:8080)
    participant Cognito as Cognito Hosted UI
    participant Identity as AgentCore Identity
    participant Gateway as AgentCore Gateway
    participant YouTube as YouTube API

    Note over User,Cognito: インバウンド認証（Cognito認可コードフロー）
    User->>Browser: http://localhost:8080 を開く
    Browser->>Server: GET /
    Server-->>Browser: "Cognitoでログイン"ボタン表示
    Browser->>Cognito: ログインクリック → 認可コードフロー
    Note over Cognito: ユーザー名/パスワード入力
    Cognito-->>Browser: 認証コードでリダイレクト
    Browser->>Server: GET /cognito/callback?code=XXX
    Server->>Cognito: コードをアクセストークンと交換
    Cognito-->>Server: アクセストークン（subクレーム含むJWT）
    
    Note over Server,Gateway: 初回リクエスト（アウトバウンドOAuthトークンなし）
    Server->>Gateway: アクセストークンでYouTubeツール呼び出し
    Gateway->>Identity: 認可検証を委任
    Identity->>Cognito: アクセストークン検証
    Cognito-->>Identity: トークン有効（subクレーム）
    Identity-->>Gateway: 認可済み
    Gateway->>Identity: ユーザーのYouTube OAuthトークン確認
    Identity-->>Gateway: YouTubeトークンなし
    Gateway-->>Server: OAuth elicitation URL を返す
    Server-->>Browser: "YouTubeを承認"メッセージ表示
    
    Note over Browser,Identity: アウトバウンドOAuth認可（YouTube）
    Browser->>YouTube: elicitation URL をクリック
    Note over YouTube: YouTube アクセスを承認
    YouTube->>Identity: 認可コードでリダイレクト
    Identity->>Server: /oauth2/callback?session_id=X&bearer_token=Yにリダイレクト
    Server->>Identity: complete_resource_token_auth(session_id, bearer_token)
    Note over Identity: コードをYouTubeトークンと交換<br/>ユーザーにバインドしてトークン保存（subクレーム経由）
    Identity-->>Server: YouTubeトークン保存完了
    
    Note over Server,YouTube: 2回目のリクエスト（アウトバウンドOAuth認可済み）
    Server->>Gateway: アクセストークンでYouTubeツール呼び出しを再試行
    Gateway->>Identity: 認可検証を委任
    Identity-->>Gateway: 認可済み（キャッシュ）
    Gateway->>Identity: ユーザーのYouTube OAuthトークン取得
    Identity-->>Gateway: YouTubeアクセストークンを返す
    Gateway->>YouTube: GET /channels（OAuthトークンで）
    YouTube-->>Gateway: チャンネルデータ
    Gateway-->>Server: チャンネルレスポンス
    Server-->>Browser: YouTubeデータを含む挨拶を表示
```

#### 重要な概念

ここで重要な概念についてお話ししておきましょう。

**2つの独立したOAuthフロー**があるんですが、これがポイントなんです。

一つ目は**Cognito認可コードフロー**、インバウンドのやつですね。

スコープとしては`openid`と`youtube-gateway-resources/youtube-target`を使います。何のためかというと、Gatewayにアクセスするためのアクセストークンを取得するためなんです。`sub`クレームがユーザーを一意に識別してくれます。

二つ目は**YouTube OAuthフロー**、アウトバウンドの方です。

こっちのスコープは`https://www.googleapis.com/auth/youtube.readonly`を使います。目的はAPI呼び出し用のYouTubeアクセストークンを取得することで、これも`sub`クレームを介してユーザーにバインドされるんですね。

**じゃあ、なんでカスタムスコープが必要なの？**って疑問に思いますよね。

これはですね、Gatewayがアウトバウンド認証にOAuth認証情報プロバイダーを使用する際に、JWTに`youtube-gateway-resources/youtube-target`スコープが必要になるからなんです。仕組みとして必要なんですね。

#### 構築プロセス

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant Construct as construct.py
    participant IAM as AWS IAM
    participant Cognito as AWS Cognito
    participant Identity as AgentCore Identity
    participant Provider as OAuth認証情報プロバイダー
    participant Gateway as AgentCore Gateway
    participant Target as Gateway Target

    Dev->>Construct: construct.py を実行
    
    Note over Construct,IAM: ステップ1: Gateway IAM Role作成
    Construct->>IAM: create_role(trust policy)
    IAM-->>Construct: role_arn
    
    Note over Construct,Cognito: ステップ2: Cognito作成（インバウンド認証）
    Construct->>Cognito: create_user_pool()
    Cognito-->>Construct: user_pool_id
    Construct->>Cognito: create_user_pool_client()
    Cognito-->>Construct: client_id, discovery_url
    
    Note over Construct,Identity: ステップ3: ワークロードID作成
    Construct->>Identity: create_workload_identity(<br/>  allowedResourceOauth2ReturnUrls<br/>)
    Identity-->>Construct: identity_arn
    
    Note over Construct,Provider: ステップ4: OAuth認証情報プロバイダー作成
    Construct->>Provider: create_oauth2_credential_provider(<br/>  YouTube client_id, client_secret<br/>)
    Provider-->>Construct: provider_arn, callback_url
    
    Note over Construct,Gateway: ステップ5: Gateway作成
    Construct->>Gateway: create_gateway(<br/>  authorizerConfig: Cognito<br/>)
    Gateway-->>Construct: gateway_id, gateway_url
    
    Note over Construct,Target: ステップ6: Gateway Target作成
    Construct->>Target: create_gateway_target(<br/>  provider_arn,<br/>  YouTube OpenAPI spec<br/>)
    Target-->>Construct: target_id
    
    Construct->>Dev: config.json を保存
```

#### 実装例

**エージェントコア（agent.py）**

```python
def call_gateway_tool(gateway_url, bearer_token, tool_name, arguments):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
        "MCP-Protocol-Version": "2025-11-25"  # OAuth elicitationに必要
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
            # ⚠️ _metaフィールドなし - ELB 403エラーの原因となる
        }
    }
    
    response = requests.post(gateway_url, headers=headers, json=payload)
    return response.json()
```

**なぜ生のJSON-RPC?**

Strands MCPクライアントはプロトコルバージョン`2025-03-26`を使用しますが、これはOAuth URL elicitationをサポートしていません。バージョン`2025-11-25`が必要です。

**OAuth2コールバックサーバー（oauth2_callback_server.py）**

```python
class OAuth2CallbackServer:
    def __init__(self, region, config):
        self.app = FastAPI()
        self.identity_client = boto3.client("bedrock-agentcore", region_name=region)
        self.access_token = None  # Cognito認証後に保存
        
    def _handle_cognito_callback(self, code):
        # 認証コードをアクセストークンと交換
        access_token = exchange_code_for_token(code)
        self.access_token = access_token
        
        # YouTube OAuth elicitationをトリガー
        result = call_gateway_tool(...)
        if "error" in result:
            auth_url = extract_elicitation_url(result)
            return display_auth_url(auth_url)
    
    def _handle_youtube_callback(self, session_id, bearer_token):
        # YouTube OAuthを完了
        self.identity_client.complete_resource_token_auth(
            sessionId=session_id,
            userToken=bearer_token
        )
        # 保存されたアクセストークンでGateway呼び出しを再試行
        return greet_user(self.access_token)
```

#### クイックスタート

```bash
cd oauth-gateway-from-browser

# 環境変数をコピー
cp .env.example .env

# AgentCoreコンポーネントを構築
uv run python construct.py

# Cognitoユーザーを作成（初回のみ）
uv run python main.py --signup --username myuser --password MyPass123!

# デモを実行
uv run python main.py
```

#### セキュリティ考慮事項

**認証情報管理:**
- 認証情報をハードコードしない
- AWS Secrets Managerまたは環境変数を使用
- OAuth シークレットの定期的なローテーション

**コールバックURLのベアラートークン:**
- 本番環境ではHTTPSが必須（bearer_tokenがクエリパラメータで渡される）
- ログからクエリパラメータを除外
- ステートレス設計により、同時OAuth フロー での競合状態を排除

**入力検証:**
- OAuthの state を検証してCSRF攻撃を防止
- ユーザー入力のサニタイゼーション
- JWT検証はAgentCore Identityが自動的に実行

---

## アーキテクチャコンセプト

さて、ここからはアーキテクチャのコンセプトについて深掘りしていきたいと思います。

### AgentCore Gateway

AgentCore Gatewayっていうのはですね、エージェントと外部APIを橋渡しする**MCPサーバー**として機能するんです。しかも、認証と認可を組み込みで提供してくれる優れものなんですよ。

#### Gatewayの役割

Gatewayが何をしてくれるのか、ちょっと整理してみましょう。

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AgentCore Gateway                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. インバウンド認証: "このユーザーは誰か？"                          │
│     - CognitoからのJWTを検証（CUSTOM_JWT authorizer）               │
│     - ユーザーIDを抽出（subクレーム、identitiesクレーム）            │
│                                                                     │
│  2. ワークロードID: "このアプリケーションは何か？"                    │
│     - GatewayはAgentCore内に独自のIDを持つ                          │
│     - ユーザートークンのスコープ: (Gateway + User) → 一意のトークン  │
│     - OAuthフロー用の信頼されたコールバックURLを定義                  │
│                                                                     │
│  3. アウトバウンド認証: "このユーザーは何にアクセスできるか？"         │
│     - Token VaultからユーザーのAPIトークンを取得                     │
│     - トークンが見つからない場合はOAuthフローをトリガー（elicitation）│
│     - 外部APIへのリクエストにトークンを注入                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

一つ目は**インバウンド認証**です。「このユーザーは誰か？」って確認するわけですね。CognitoからのJWTを検証して、ユーザーIDを抽出します。

二つ目が**ワークロードID**です。これは「このアプリケーションは何か？」を定義するものです。GatewayはAgentCore内に独自のIDを持っていて、ユーザートークンのスコープを管理します。

三つ目が**アウトバウンド認証**です。「このユーザーは何にアクセスできるか？」をチェックするんですね。Token VaultからユーザーのAPIトークンを取得して、トークンが見つからない場合はOAuthフローをトリガーします。

#### ワークロードIDとは

ワークロードIDって、最初聞くとちょっと分かりにくいかもしれないんですけど、実は重要な概念なんです。

Gatewayを作成するとですね、AgentCoreが自動的に**ワークロードID**を作成してくれるんです。これはAgentCoreの世界におけるGatewayの「企業ID」みたいなものだと考えてください。

```
ワークロードID = "mcp-oauth-gateway-gateway-xyz"
        │
        ├── このGatewayアプリケーションを表す
        │
        ├── Token Vaultのエントリは（ワークロードID + ユーザー）にスコープされる
        │   └── 異なるGateway を通じた同じユーザー = 別々のトークン
        │
        └── allowedResourceOauth2ReturnUrls
            └── OAuthセッションバインディング用の信頼されたコールバックURL
```

**じゃあ、なんでワークロードIDがOAuthに重要なのか？**

これをですね、会社が従業員のリクエストを処理するようなものとして考えてみましょう。面白い例えなんですよ。

```
ワークロードID = "Acme Corp Gateway"（会社）
ユーザー（JWT）= IDバッジを持つ従業員
Token Vault    = セキュアなファイリングキャビネット
session_id     = リクエストフォーム番号

シナリオ: 従業員BがYouTube APIアクセスを必要とする

1. 従業員B（JWT）がAcme Corp ビルに入る
2. セキュリティが検証: "このバッジはAcme Corp製？" ✓
3. 従業員B: "YouTubeアクセスが必要"
4. Acme Corpがファイリングキャビネットを確認: 
   "Acme Corp → 従業員B → YouTube... 見つかりません"
5. Acme Corp: "承認フォーム#session_idに記入し、Googleに承認を取りに行ってください"
6. 従業員BがGoogleでOAuthを完了
7. GoogleがAcme Corpの登録された住所に従業員Bを返送
   （allowedResourceOauth2ReturnUrls = 会社の信頼された郵便室）
8. Acme Corp郵便室が検証: "これは本当に従業員Bが自分のフォームを完了しているか？"
   → CompleteResourceTokenAuth(session_id, 従業員Bのバッジ)を呼び出す
9. AgentCoreが保存: "Acme Corp → 従業員B → YouTube → [トークン]"
```

こういう風に考えるとですね、ワークロードIDの役割がよく分かりますよね。

#### Gatewayの構成

```python
# インバウンド: Cognito JWT検証
authorizerType="CUSTOM_JWT"
authorizerConfiguration={
    "customJWTAuthorizer": {
        "discoveryUrl": cognito_discovery_url,
        "allowedClients": [cognito_client_id]
    }
}

# アウトバウンド: 3LO用のセッションバインディングを持つOAuth
credentialProviderConfigurations=[{
    "credentialProviderType": "OAUTH",
    "credentialProvider": {
        "oauthCredentialProvider": {
            "providerArn": outbound_provider_arn,
            "grantType": "AUTHORIZATION_CODE",
            "defaultReturnUrl": callback_url,
            "scopes": ["https://www.googleapis.com/auth/youtube.readonly"]
        }
    }
}]
```

### Token Vault（トークンボルト）

Token Vaultは、AgentCore Identityが提供するセキュアなトークンストレージサービスです。

#### 主な特徴

- **ユーザーごとのトークン隔離**: 各ユーザーのトークンを個別に保存
- **自動ライフサイクル管理**: トークンの更新と有効期限管理を自動化
- **暗号化ストレージ**: AWS KMSによる暗号化
- **スコープされたアクセス**: （ワークロードID + ユーザーID）でトークンを管理

#### トークンバインディングフロー

```
1. ユーザーがYouTubeデータをリクエスト → Gatewayがゲートウェイ がToken Vaultを確認 → トークンなし
2. GatewayがVault がsession_idを含む認証URLでelicitationを返す
3. ユーザーがGoogleでOAuthを完了
4. GoogleがAgentCoreにリダイレクト → AgentCoreがあなたのコールバックにリダイレクト
5. あなたのコールバックがCompleteResourceTokenAuth(session_id, userToken)を呼び出す
   - session_id: この認可試行を識別
   - userToken: ユーザーIDを証明するインバウンドJWT
6. AgentCoreがVaultにトークンを保存: （ワークロードID + ユーザー） → YouTubeトークン
7. 以降のリクエストは保存されたトークンを自動的に使用
```

### OAuth認証情報プロバイダー

OAuth認証情報プロバイダーは、外部サービス（例: Google、GitHub）のOAuth構成を管理します。

#### 2種類のプロバイダー

| プロバイダータイプ | 目的 | 例 |
|------------------|------|-----|
| **インバウンド** | ユーザーID | Cognito（Google連携） |
| **アウトバウンド** | APIアクセス | Google（YouTube API） |

#### プロバイダーの作成

```python
control_client = boto3.client("bedrock-agentcore-control")

# アウトバウンドプロバイダー（YouTube OAuth）
provider_response = control_client.create_oauth2_credential_provider(
    name="youtube-oauth-provider",
    credentialProviderVendor="GoogleOauth2",
    oauth2ProviderConfigInput={
        "googleOauth2ProviderConfig": {
            "clientId": youtube_client_id,
            "clientSecret": youtube_client_secret
        }
    }
)

provider_arn = provider_response["providerArn"]
callback_url = provider_response["callbackUrl"]  # Googleに登録
```


---

## 技術スタック

それでは、使用されている技術スタックについて見ていきましょう。

### プログラミング言語とランタイム

まず基本となる言語とランタイムですが、**Python 3.10以上**をすべての例で使ってます。そして**uv**という高速で信頼性の高い依存関係管理ツールを採用してるんですね。

### AWS サービス

AWSサービスはですね、いくつか使ってます。

中心となるのが**Amazon Bedrock AgentCore**です。これはAIエージェントのための統合認証・認可サービスなんですね。その中にGatewayというMCPプロトコルのエンドポイントと、IdentityというOAuthトークン管理とユーザーIDバインディングの仕組みがあります。

それから**Amazon Cognito**でユーザー認証とID連携を行います。

**AWS Lambda**はサーバーレスのOAuthコールバック処理に使っていて、**Amazon CloudFront**でコンテンツ配信とDDoS保護を実現してます。

**Amazon DynamoDB**はOAuthセッション状態の一時保存用で、**AWS KMS**がトークンの暗号化を担当してます。もちろん、**AWS IAM**で権限管理もしっかりやってます。

### AgentCore 関連ライブラリ

AgentCore関連のライブラリも見ておきましょう。

```toml
[project.dependencies]
bedrock-agentcore = ">=0.1.1"
bedrock-agentcore-starter-toolkit = ">=0.1.2"
boto3 = ">=1.39.9"
```

**bedrock-agentcore**はAgentCore Identity APIとデコレータを提供してくれます。`@requires_access_token`でOAuthフローを簡略化できるんですよ。

**bedrock-agentcore-starter-toolkit**はGateway作成のヘルパーなんですが、OAuth用には生のboto3を使うことを推奨してます。

**boto3**はAWSサービスへの直接アクセスに使います。`bedrock-agentcore-control`でGatewayやIdentityの作成を、`bedrock-agentcore`でランタイム操作を行います。

### エージェントフレームワーク

エージェントフレームワークとしては**Strands**を使ってます。

```toml
strands-agents = ">=1.0.1"
strands-agents-tools = ">=0.2.1"
```

これは軽量のAIエージェントフレームワークで、`Agent`でツールを使用した会話エージェントを作れますし、`MCPClient`でMCPプロトコルをサポートできるんです。

### Web フレームワーク

Webフレームワークは**FastAPI**と**Uvicorn**を使ってます。

```toml
fastapi = ">=0.115.0"
uvicorn = ">=0.32.0"
```

FastAPIは最新の高速Webフレームワークで、OAuthコールバックエンドポイントの実装に使ってます。非同期サポートもあって、自動OpenAPIドキュメントも生成してくれるんです。便利ですよね。

UvicornはASGIサーバーとして動きます。

### MCP（Model Context Protocol）

MCPには**FastMCP**を使ってます。

```toml
fastmcp = ">=0.1.0"
```

これはMCPサーバー実装用のライブラリで、MCPプロトコル自体はエージェントとツール間の標準化された通信プロトコルなんです。バージョン`2025-11-25`ではOAuth URL elicitationをサポートしてます。

### ユーティリティライブラリ

その他のユーティリティライブラリもいくつか使ってますね。

```toml
pyjwt = ">=2.9.0"           # JWT デコード
python-dotenv = ">=1.0.0"   # 環境変数管理
requests = ">=2.32.5"       # HTTP クライアント
```

JWTデコード、環境変数管理、HTTPクライアントという基本的なものですね。

### 開発ツール

開発用のツールもしっかり揃えてます。

```toml
[dependency-groups.dev]
ruff = ">=0.14.8"           # リンター/フォーマッター
pytest = ">=8.3.0"          # テストフレームワーク
selenium = ">=4.27.0"       # ブラウザ自動化（テスト用）
```

リンター、テストフレームワーク、ブラウザ自動化ツールですね。

### 依存関係管理

依存関係の管理についてもちょっと触れておきましょう。

**pyproject.toml の構造**はこんな感じです。

```toml
[project]
name = "agentcore-examples"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # コア依存関係
]

[dependency-groups]
dev = [
    # 開発専用依存関係
]
```

**インストールコマンド**も簡単です。

```bash
# すべての依存関係をインストール（開発用を含む）
uv sync

# 本番環境の依存関係のみ
uv sync --no-dev
```

開発用と本番用で分けられるのがいいですよね。

---

## ユースケースと実用例

それでは、実際のユースケースと実用例について見ていきましょう。

### 1. セキュアなAPIゲートウェイ

まず一つ目のユースケースです。

**シナリオ**としてはですね、複数のサードパーティAPIにアクセスする必要があるエンタープライズアプリケーションの場合です。よくあるケースですよね。

**AgentCoreソリューション**としては、Gatewayが中央認証ポイントとして機能してくれるんです。ユーザーごとにトークンを隔離して、APIキーの一元管理ができます。監査ログとコンプライアンスもしっかり対応してます。

**メリット**は何かというと、API認証情報をアプリケーションコードから分離できることですね。ユーザーごとの細かいアクセス制御もできますし、自動トークン更新もあります。組み込みのセキュリティベストプラクティスもついてくるので安心です。

### 2. マルチテナントSaaSアプリケーション

次は二つ目のユースケースです。

**シナリオ**は、各テナントが独自の外部サービス統合を持つSaaSプラットフォームの場合ですね。これも結構あるパターンです。

**AgentCoreソリューション**では、ワークロードIDによってテナントを分離できます。テナントごとにOAuth構成ができて、スケーラブルなトークン管理が可能です。CloudFrontによるグローバル分散もできちゃうんです。

**メリット**としては、テナント間のデータ隔離が保証されることですね。テナントごとに独立した認証フローが持てますし、運用オーバーヘッドも削減できます。自動スケーリングとフォールトトレランスもあるので、安定運用できるわけです。

### 3. AI エージェント用ツールエコシステム

三つ目はAIエージェントのユースケースです。

**シナリオ**は、様々な外部ツールにアクセスする必要があるAIエージェントですね。これ、最近増えてきてるパターンです。

**AgentCoreソリューション**では、MCPプロトコルによって標準化されたツールインターフェースを提供します。OAuth経由でセキュアにツール認証ができて、動的なツール検出もできます。ツール呼び出しの文脈管理もしっかりしてるんです。

**メリット**は、ツール統合が簡素化されることですね。一貫したセキュリティモデルが使えますし、プラガブルなアーキテクチャになってます。ベンダーロックインも回避できるので、柔軟性が高いんです。

### 4. ユーザー委任アクセス

四つ目のユースケースです。

**シナリオ**は、ユーザーの代わりに個人データにアクセスする必要があるアプリケーションの場合です。プライバシーが重要なケースですね。

**AgentCoreソリューション**では、OAuth 2.0の認可コードフローを使います。明示的なユーザー同意を取って、スコープベースの権限管理ができます。Token Vaultでセキュアに保存されるので安心です。

**メリット**としては、ユーザー認証情報を保存しないことですね。細かい権限制御ができますし、ユーザーが自分でアクセスを取り消すこともできます。GDPRやプライバシーコンプライアンスにも対応できるわけです。

### 5. マイクロサービスアーキテクチャ

五つ目のユースケースです。

**シナリオ**は、サービス間の認証が必要なマイクロサービス環境ですね。最近のアーキテクチャでは一般的になってきました。

**AgentCoreソリューション**では、Gatewayがサービスメッシュのエッジとして機能します。
- サービス間のトークン伝播
- 一元化された認証ポリシー
- IAM統合

**メリット**としては、サービス認証が簡素化されることですね。一貫したセキュリティポリシーが適用できますし、監査とモニタリングも向上します。ゼロトラストアーキテクチャもサポートしてるので、セキュアな環境を構築できるわけです。

### 6. 開発者向けツールとCLI

最後、六つ目のユースケースです。

**シナリオ**は、複数のクラウドサービスと対話するCLIツールの場合ですね。開発者にはよくある話です。

**AgentCoreソリューション**では、ローカル開発用のOAuthフローが提供されます。トークンキャッシングもあって、複数プロファイルのサポートもあります。ブラウザベースの認証もできるんです。

**メリット**は、スムーズな開発者体験が得られることですね。セキュアな認証情報管理ができて、クロスプラットフォームにも対応してます。企業のIDプロバイダーとの統合もできるので、エンタープライズ環境でも使いやすいんです。

---

## セットアップ要件

それでは、セットアップに必要なものを見ていきましょう。

### 前提条件

#### AWS 要件

まずAWS側の要件からです。

一つ目、**AWSアカウント**が必要です。当然ですが、AgentCoreサービスへのアクセスが必要ですね。

適切なIAM権限も必要で、`bedrock-agentcore:*`、`cognito-idp:*`、`iam:CreateRole`と`iam:AttachRolePolicy`、それから`lambda:*`、`cloudfront:*`、`dynamodb:*`、`kms:*`といった権限が必要になります。

二つ目、**AWS認証情報の構成**をする必要があります。

いくつかオプションがあるんですが、

```bash
# オプション 1: AWS CLI 構成
aws configure

# オプション 2: 環境変数
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1

# オプション 3: IAM Role（EC2/ECS/Lambda）
# インスタンスプロファイルまたはタスクロールを使用
```

こんな感じで設定できます。

三つ目、**サービスクォータ**も確認しておきましょう。

AgentCore Gatewayはリージョンあたり10
   - Cognito User Pools: リージョンあたり1000
   - Lambda 同時実行: 少なくとも10

#### Google Cloud 要件

1. **Google Cloud Console プロジェクト**
   - [Google Cloud Console](https://console.cloud.google.com/)にアクセス
   - 新しいプロジェクトを作成または既存のものを選択

2. **YouTube Data API v3を有効化**
   ```
   1. APIs & Services → Library
   2. "YouTube Data API v3" を検索
   3. "Enable" をクリック
   ```

3. **OAuth 2.0 認証情報の作成**
   ```
   1. APIs & Services → Credentials
   2. Create Credentials → OAuth 2.0 Client ID
   3. Application type: Web application
   4. Name: YouTube Gateway Example
   5. Authorized redirect URIs: 
      - 後で追加（construct.py実行後）
   6. Create
   7. Client IDとClient Secretを保存
   ```

#### ローカル開発環境

1. **Python 3.10以上**
   ```bash
   # バージョン確認
   python --version
   
   # 必要に応じてインストール
   # macOS (Homebrew):
   brew install python@3.10
   
   # Ubuntu/Debian:
   sudo apt update
   sudo apt install python3.10 python3.10-venv
   
   # Windows:
   # https://www.python.org/downloads/ からインストーラーをダウンロード
   ```

2. **uv（依存関係管理）**
   ```bash
   # インストール
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # または pip 経由:
   pip install uv
   
   # バージョン確認
   uv --version
   ```

3. **Git**
   ```bash
   # インストール確認
   git --version
   
   # 必要に応じてインストール
   # macOS: brew install git
   # Ubuntu: sudo apt install git
   # Windows: https://git-scm.com/download/win
   ```

### リポジトリのクローン

```bash
# リポジトリをクローン
git clone https://github.com/icoxfog417/agentcore-in-action.git
cd agentcore-in-action

# 依存関係をインストール
uv sync
```

### 環境構成

#### 1. 環境変数の設定

各プロジェクトには`.env.example`ファイルがあります：

```bash
# oauth-gateway-from-browser の例
cd oauth-gateway-from-browser
cp .env.example .env
```

**.env ファイルを編集:**

```bash
AWS_REGION=us-east-1
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret
CALLBACK_URL=http://localhost:8080/oauth2/callback
```

#### 2. AWS リソースの構築

```bash
# AgentCoreコンポーネントを作成
uv run python construct.py
```

**construct.py の出力例:**

```
✓ Gateway IAM Roleを作成しました: arn:aws:iam::123456789012:role/...
✓ Cognito User Poolを作成しました: us-east-1_XXXXX
✓ Workload Identityを作成しました: arn:aws:bedrock-agentcore:...
✓ OAuth Credential Providerを作成しました: arn:aws:bedrock-agentcore:...

⚠ 重要: 以下のURLをGoogle Cloud Consoleに登録してください:
   oauth_callback_url: https://bedrock-agentcore.amazonaws.com/identities/callback/...

✓ Gatewayを作成しました: youtube-gateway (READY)
✓ Gateway Targetを作成しました: YouTubeTarget

構成をconfig.jsonに保存しました
```

#### 3. Google OAuth コールバックURLの登録

1. [Google Cloud Console](https://console.cloud.google.com/)に移動
2. APIs & Services → Credentials
3. OAuth 2.0 Client IDを選択
4. "Authorized redirect URIs"に`oauth_callback_url`を追加（construct.pyの出力から）
5. 保存

#### 4. Cognitoユーザーの作成（初回のみ）

```bash
# oauth-gateway-from-browser の場合
uv run python main.py --signup --username myuser --password MyPass123!
```

### 検証

```bash
# デモを実行
uv run python main.py

# 期待される出力:
# ✓ 構成を読み込みました
# ✓ サーバーが http://localhost:8080 で起動しました
# ブラウザでアクセスしてください...
```

### クリーンアップ

```bash
# すべてのAWSリソースを削除
uv run python construct.py --cleanup
```

**注意**: クリーンアップは以下の順序で実行されます：
1. Gateway Target
2. Gateway
3. OAuth Provider
4. Workload Identity
5. Cognito リソース
6. IAM Role

---

## 開発者向けガイド

### リポジトリ構造

各例は同じ構造に従います：

```
example_name/
├── README.md              # 包括的なドキュメント
├── main.py                # エントリーポイントスクリプト
├── construct.py           # AWS リソース構築（複雑な例の場合）
├── .env.example           # 環境変数テンプレート
├── .progress              # 開発イテレーションログ
├── tests/                 # 仕様に基づいたテストケース
│   ├── README.md          # テスト構造の概要
│   └── test_main.py
└── example_name/          # コア実装
    ├── __init__.py
    ├── agent.py
    └── utils.py
```

### 開発ワークフロー

本リポジトリは**仕様主導開発**アプローチに従います：

#### 1. 仕様定義

`README.md`で期待される動作とインターフェースを定義：

```markdown
## 仕様

### コンポーネントの責任

| コンポーネント | 責任 |
|---------------|------|
| **Gateway** | JWT検証、APIプロキシ |
| **Identity** | トークン保存、OAuth管理 |
| **Agent** | ツール呼び出しオーケストレーション |
```

#### 2. テスト設計

`tests/README.md`でテスト構造を文書化：

```markdown
# テストスイート概要

## カテゴリ

### 構成
- test_load_config_success
  - 仕様: README.md > 仕様 > 構成
  - 目的: 環境変数が正しく読み込まれる
  - ステータス: ✅

### 認証
- test_oauth_flow
  - 仕様: README.md > 仕様 > OAuth フロー
  - 目的: OAuth elicitationを正しく処理
  - ステータス: ❌ (TODO)
```

#### 3. 実装

テストを満たす最小限のコードを実装：

```python
def load_config() -> dict:
    """構成ファイルから設定を読み込む。
    
    テスト: tests/test_config.py::test_load_config_success
    """
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError("config.json not found")
    with open(config_path) as f:
        return json.load(f)
```

#### 4. テストと評価

```bash
# すべてのテストを実行
uv run pytest tests/ -v

# 失敗したテストのみ再実行
uv run pytest tests/ -v --lf

# カバレッジレポート
uv run pytest tests/ --cov=example_name --cov-report=html
```

`.progress`ファイルに結果を記録：

```markdown
## イテレーション 1: [2024-01-15]

### 仕様
- 目標: 基本的な構成読み込みを実装
- 主な決定: JSON ファイルベースの構成

### 実装
- コード変更: config.py に load_config() を追加

### テスト
- コマンド: uv run pytest tests/ -v
- 結果: 5/5 合格

### 評価
- うまくいったこと: シンプルな実装、明確なエラーメッセージ
- 課題: なし
- 次のイテレーションの焦点: OAuth フロー の実装
```

### コーディング規約

#### Python スタイル

```bash
# Ruff でリント
uv run ruff check .

# 自動修正
uv run ruff check --fix .

# フォーマット
uv run ruff format .
```

#### ドキュメント規約

- **Docstrings**: Google スタイル
- **型ヒント**: すべての公開関数
- **コメント**: 複雑なロジックのみ

```python
def extract_user_id(token: str) -> str:
    """JWTトークンからユーザーIDを抽出。
    
    Args:
        token: Base64エンコードされたJWTトークン
        
    Returns:
        `sub`クレームからのユーザーID
        
    Raises:
        ValueError: トークンが無効な場合
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        return decoded["sub"]
    except (IndexError, KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid JWT token: {e}")
```

### テストのベストプラクティス

#### 構造

```python
# tests/test_agent.py
import pytest
from example_name.agent import greet_user

class TestGreetUser:
    """greet_user関数のテスト。
    
    仕様: README.md > 仕様 > エージェント > greet_user
    """
    
    def test_successful_greeting(self, mock_gateway, mock_token):
        """有効なトークンでの成功した挨拶。"""
        result = greet_user(mock_gateway, mock_token)
        assert "Hello" in result
        assert mock_gateway.call_count == 1
    
    def test_oauth_elicitation(self, mock_gateway_no_token):
        """トークンなしでのOAuth elicitation処理。"""
        result = greet_user(mock_gateway_no_token, "token")
        assert "authorization" in result.lower()
```

#### モッキング

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_gateway():
    """成功レスポンスを持つモックGateway。"""
    gateway = Mock()
    gateway.call_tool.return_value = {
        "content": [{"text": "Hello, User!"}]
    }
    return gateway

@pytest.fixture
def mock_identity_client():
    """モックIdentity クライアント。"""
    client = Mock()
    client.complete_resource_token_auth.return_value = {}
    return client
```

### トラブルシューティングガイド

#### 一般的な問題

**1. "ResourceAlreadyExists" エラー**

```bash
# 解決策: 既存のリソースをクリーンアップ
uv run python construct.py --cleanup
uv run python construct.py
```

**2. "AccessDenied" 作成時**

```bash
# IAM 権限を確認
aws iam get-user
aws sts get-caller-identity

# 必要なポリシー:
# - bedrock-agentcore:*
# - cognito-idp:*
# - iam:CreateRole
```

**3. OAuth コールバックが完了しない**

```bash
# コールバックサーバーが実行中か確認
curl http://localhost:8080/

# Google OAuth コールバックURLを確認
# config.jsonからoauth_callback_urlを確認
# Google Cloud Consoleで登録されているか確認
```

**4. Gateway ツールが見つからない**

```bash
# Gateway のステータスを確認
aws bedrock-agentcore get-gateway \
    --gateway-identifier <gateway-id> \
    --region us-east-1

# ステータスが"READY"であることを確認
# そうでない場合は、作成が完了するまで待つ（2-5分）
```

#### デバッグのヒント

**ログレベルを有効化:**

```bash
export LOG_LEVEL=DEBUG
uv run python main.py
```

**boto3 デバッグログ:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```

**MCP プロトコルトレース:**

```python
import os
os.environ["MCP_DEBUG"] = "1"
```

### コントリビューションガイドライン

#### 新しい例を追加する

1. **仕様を作成**: `README.md`から開始
2. **テストを設計**: `tests/README.md`を作成
3. **実装**: テストを満たすコードを書く
4. **文書化**: セキュリティ考慮事項を追加
5. **検証**: チェックリストを完了

#### チェックリスト

- [ ] README.mdの仕様が完全で明確
- [ ] tests/README.mdが README.mdの仕様と一致
- [ ] すべてのテストが合格: `uv run pytest tests/ -v`
- [ ] リントがクリーン: `uv run ruff check`
- [ ] 手動実行が成功: `uv run python main.py`
- [ ] .progressファイルがすべてのイテレーションを文書化
- [ ] フレッシュ環境でテスト済み
- [ ] ドキュメントリンクが検証済み
- [ ] セキュリティ考慮事項が文書化済み

### 参考リンク

#### AgentCore ドキュメント

- [AgentCore Gateway 概要](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway.html)
- [AgentCore Identity - Token Vault](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-identity.html)
- [OAuth 2.0 認証情報プロバイダー](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-identity-oauth.html)
- [AgentCore Identity API リファレンス](https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/identity.md)
- [AgentCore Gateway 統合ガイド](https://aws.github.io/bedrock-agentcore-starter-toolkit/examples/gateway-integration.md)

#### OAuth & セキュリティ

- [OAuth 2.0 認可コードグラント](https://oauth.net/2/grant-types/authorization-code/)
- [OAuth 2.0 セキュリティベストプラクティス](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [AWS セキュリティベストプラクティス](https://docs.aws.amazon.com/security/)

#### Google APIs

- [Google OAuth 2.0 設定](https://developers.google.com/identity/protocols/oauth2/web-server#creatingcred)
- [Google APIスコープ](https://developers.google.com/identity/protocols/oauth2/scopes)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [YouTube OAuth 認証ガイド](https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps)

#### MCP プロトコル

- [MCP 仕様](https://spec.modelcontextprotocol.io/)
- [MCP 認証](https://spec.modelcontextprotocol.io/specification/architecture/#authentication)
- [MCP URL モード Elicitation](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/#url-mode-elicitation-secure-out-of-band-interactions)

---

## まとめ

さて、ここまで色々とお話ししてきましたが、最後にまとめていきたいと思います。

**agentcore-in-action**リポジトリですけど、これはAWS Bedrock AgentCoreを使ったOAuth統合の実践的な実装例を提供してくれるんですね。

2つの主要プロジェクト、oauth-gateway-from-agentとoauth-gateway-from-browserを通じてですね、セキュアなMCPサーバーの構築方法、ユーザー認証とAPIアクセスの統合方法、そして本番環境で考慮すべきセキュリティ要件を学べるわけです。

### 主な利点

じゃあ、このリポジトリの主な利点って何なんでしょうか？いくつか挙げてみましょう。

まず**実用的**ですよね。すぐに実行可能なスクリプトベースの例が用意されているので、理論だけじゃなくて実際に動かせるんです。

それから**包括的**です。アーキテクチャから実装まで完全にドキュメント化されているので、迷うことがありません。

**セキュア**であることも重要なポイントです。本番環境を意識したセキュリティベストプラクティスが組み込まれてます。

**再現可能**なのもいいですよね。`uv`による確実な依存関係管理があるので、誰が実行しても同じ結果が得られます。

そして**教育的**です。仕様、テスト、実装の完全なワークフローを学べるので、単なるコピペじゃなくて理解しながら進められるんですね。

### 次のステップ

「じゃあ、これから何をすればいいの？」って思いますよね。次のステップをいくつか提案しておきましょう。

まず一つ目、**環境をセットアップ**してください。AWSとGoogle認証情報を取得する必要があります。

二つ目、**例を実行**してみましょう。両方のプロジェクトを試して、実際にどう動くのか理解してください。

三つ目、**カスタマイズ**です。自分のユースケースに合わせて適応させていきましょう。

四つ目が**デプロイ**ですね。本番環境のセキュリティ考慮事項をしっかり守ってデプロイしてください。

最後に、もしよかったら**貢献**してください。コミュニティと知見を共有することで、みんなで成長していけますからね。

### サポートとコミュニティ

サポートやコミュニティについてもお知らせしておきます。

**リポジトリ**は[github.com/icoxfog417/agentcore-in-action](https://github.com/icoxfog417/agentcore-in-action)にあります。

**Issues**でバグ報告と機能リクエストができますし、**Discussions**で質問とアイデアの共有もできます。

一緒にAgentCoreでセキュアで強力なAIエージェントアプリケーションを構築していきましょう！

---

**ライセンス**: 本リポジトリは教育および参照目的でそのまま提供されます。

**最終更新**: 2024年

