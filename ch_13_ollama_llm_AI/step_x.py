# Gemma3 모델
import ollama

resp = ollama.chat(model="gemma3:4b", messages=
                   [{"role": "user"
                    , "content": "내 이름은 김정하야!"}])
resp.model_dump() 
resp["message"]["content"]
resp.message.content

data = ollama.chat(model="gemma3:4b", messages=[{"role": "user", "content": "내 이름이 뭐였지?!"}])
print(resp_2.message.content)

data.message.content
data = resp.model_dump()
print(data)


history = []
history.append({"role": "user", "content": "내 이름은 김정하야!"})

data = ollama.chat(model="gemma3:4b", messages=history)
data.message.content
data.message.model_dump()
history.append(data.message.model_dump())

history.append({"role": "user", "content": "내 이름이 뭐였지?!"})

resp2 = ollama.chat(model="gemma3:4b", messages=history)
resp2.message.content
history.append(resp2.message.model_dump())

history

