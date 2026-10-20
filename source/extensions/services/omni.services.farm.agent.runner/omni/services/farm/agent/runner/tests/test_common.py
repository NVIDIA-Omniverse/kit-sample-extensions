import carb
import pydantic
from omni.services.core import exceptions, routers

router = routers.ServiceAPIRouter()


# NOTE: We cannot import the Pydantic data models from the controller because doing so imports the router.  Moreover,
# in most of our test cases, we don't really care about the particulars of the controller's data models.  So rather
# than duplicating those models here and having to keep them in sync, we can use this generic mock model instead.
class AnyModel(pydantic.BaseModel):
    class Config:
        extra = "allow"


class MockTaskManager:
    def __init__(self, data):
        self.data = data

    def set_data(self, data):
        self.data = data

    async def get_task(self, task_id):
        return self.data[task_id]

    async def set_task_started(self, task_id):
        self.data[task_id]["status"] = "started"

    async def set_task_finished(self, task_id):
        self.data[task_id]["status"] = "finished"

    async def set_task_errored(self, task_id, reason):
        self.data[task_id]["status"] = "errored"
        self.data[task_id]["reason"] = reason

    async def task_checkin(self, task_id, **_kwargs):
        self.data[task_id]

    async def get_logs(self, task_id):
        self.data[task_id]
        return "fake-log-data"


@router.get("/task/retrieve")
async def get_task(task_id: str, task_manager=router.get_facility("task_manager")):
    carb.log_info(f"{task_id} retrieve")
    try:
        return await task_manager.get_task(task_id=task_id)
    except KeyError:
        raise exceptions.KitServicesBaseException(status_code=404, detail="Task does not exist.")


@router.post(f"/task/started")
async def started(task: AnyModel, task_manager=router.get_facility("task_manager")):
    await task_manager.set_task_started(task.task_id)


@router.post(f"/task/finished")
async def finished(task: AnyModel, task_manager=router.get_facility("task_manager")):
    await task_manager.set_task_finished(task.task_id)
    if hasattr(task_manager, "data"):
        task_manager.data[task.task_id]["stats"] = task.dict()


@router.post(f"/task/checkin")
async def checkin(task: AnyModel, task_manager=router.get_facility("task_manager")):
    pass


@router.post(f"/task/errored")
async def errored(task: AnyModel, task_manager=router.get_facility("task_manager")):
    try:
        return await task_manager.set_task_errored(task.task_id, task.comment)
    except KeyError:
        raise exceptions.KitServicesBaseException(status_code=404, detail="Task does not exist.")
