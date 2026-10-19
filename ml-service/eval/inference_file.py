import inspect
from pipeline.model_stage import RealModel

m = RealModel.get().model
print("FIRMA:", inspect.signature(m.inference_file))
src = inspect.getsource(m.inference_file)
print(src[:3000])   # primeras líneas: busca subtask/task/condicional