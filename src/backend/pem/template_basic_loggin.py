from common.logger import log_event

log_event(
    source="pem",
    data={"prompt": "Define purpose", "result": "To live with alignment"},
    tags=["prompt", "philosophy"],
    memo="PEM identity shaping run",
)
