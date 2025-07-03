# SMRT ChatBot

## Configuration


## Send messages

```bash
curl -X POST http://localhost:5000/send_message \
  -H "Content-Type: application/json" \
  -d '{"chatIds": ["whatsapp://00000@c.us", "signal://KKKKvv+", "signal://+49166666666"], "message": "Hello!"}'
```

### For Homeassistant

```yaml
TBD
```