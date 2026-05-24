"""固定免責聲明常數。

所有排名、績效說明、隔日清單、Email 與通知都必須附上這段文字。
集中在這裡，確保整個系統的免責用語一致。
"""

# 中文（主要顯示用）
DISCLAIMER_ZH = (
    "本內容僅供資訊整理與研究參考，不構成投資建議。投資有風險，請自行評估。"
)

# 英文（Email / 國際使用者備用）
DISCLAIMER_EN = (
    "This content is for information and research reference only and does not "
    "constitute investment advice. Investing involves risk."
)

# 預設使用中文
DISCLAIMER = DISCLAIMER_ZH
