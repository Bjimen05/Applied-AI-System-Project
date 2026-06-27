from pawpal_system import Task, Pet, Priority


def make_task(**kwargs):
    defaults = dict(
        title="Test Task",
        description="A test task",
        duration_minutes=15,
        priority=Priority.MEDIUM,
        due_time=540,
    )
    return Task(**{**defaults, **kwargs})


def test_mark_complete_changes_status():
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Biscuit", species="Dog", breed="Golden Retriever", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(make_task(title="Walk"))
    pet.add_task(make_task(title="Feeding"))
    assert len(pet.tasks) == 2
