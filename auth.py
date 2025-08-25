import requests
import json
import base64
from .utils import write_json, read_json


class MicrosoftAuth:
    def __init__(self, client_id, client_secret=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = "tokens.json"

    def device_flow_auth(self):
        """设备代码流认证"""
        # 获取设备代码
        device_code_response = requests.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode",
            data={
                "client_id": self.client_id,
                "scope": "XboxLive.signin offline_access"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        device_code_response.raise_for_status()
        device_data = device_code_response.json()

        print(f"请访问 {device_data['verification_uri']} 并输入代码: {device_data['user_code']}")

        # 轮询令牌
        while True:
            token_response = requests.post(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": self.client_id,
                    "device_code": device_data["device_code"]
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            token_data = token_response.json()

            if "error" in token_data:
                if token_data["error"] == "authorization_pending":
                    time.sleep(device_data["interval"])
                    continue
                else:
                    raise Exception(f"Authentication error: {token_data['error']}")
            else:
                break

        # 保存令牌
        self._save_tokens(token_data)
        return token_data

    def xbox_live_auth(self, access_token):
        """Xbox Live认证"""
        # XBL认证
        xbl_response = requests.post(
            "https://user.auth.xboxlive.com/user/authenticate",
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={access_token}"
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT"
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        xbl_response.raise_for_status()
        xbl_data = xbl_response.json()

        # XSTS认证
        xsts_response = requests.post(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            json={
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbl_data["Token"]]
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT"
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        xsts_response.raise_for_status()
        xsts_data = xsts_response.json()

        return xbl_data, xsts_data

    def minecraft_auth(self, xbl_data, xsts_data):
        """Minecraft服务认证"""
        # 获取Minecraft访问令牌
        minecraft_response = requests.post(
            "https://api.minecraftservices.com/authentication/login_with_xbox",
            json={
                "identityToken": f"XBL3.0 x={xbl_data['DisplayClaims']['xui'][0]['uhs']};{xsts_data['Token']}"
            },
            headers={"Content-Type": "application/json"}
        )
        minecraft_response.raise_for_status()
        minecraft_data = minecraft_response.json()

        # 获取Minecraft档案
        profile_response = requests.get(
            "https://api.minecraftservices.com/minecraft/profile",
            headers={"Authorization": f"Bearer {minecraft_data['access_token']}"}
        )
        profile_response.raise_for_status()
        profile_data = profile_response.json()

        return {
            "access_token": minecraft_data["access_token"],
            "username": profile_data["name"],
            "uuid": profile_data["id"],
            "profile": profile_data
        }

    def _save_tokens(self, tokens):
        """保存令牌到文件"""
        write_json(self.token_file, tokens)

    def _load_tokens(self):
        """从文件加载令牌"""
        return read_json(self.token_file)

    def refresh_tokens(self, refresh_token):
        """刷新访问令牌"""
        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "XboxLive.signin offline_access"
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = requests.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()

        tokens = response.json()
        self._save_tokens(tokens)
        return tokens