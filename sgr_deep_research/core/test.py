from pydantic import BaseModel


class Model(BaseModel):
    name: str


model = Model(name="Name", address="bla bla", post="post")

print(model)
# name='Name' post='post' address='bla bla'
