from atlas.core.session import Session

session = Session()

print("=" * 60)
print("SESSION")
print("=" * 60)

print("ID       :", session.id)
print("Project  :", session.project)
print("User     :", session.user)
print("Status   :", session.status)

session.start("Build Atlas")

print("Running  :", session.status)
print("Task     :", session.task)

session.finish()

print("Finished :", session.status)

print("=" * 60)

assert session.status == "completed"

print("Session verified.")

print("=" * 60)
