import logging
from datetime import datetime
from core.event_bus import event_bus

# Configure logging
def configure_logging():
    logging.basicConfig(filename='/home/triad/mitch/logs/innermono.log',
                        level=logging.INFO,
                        format='%(asctime)s [ProjectManagementAssistant] %(message)s')

# Project Management Assistant class
class ProjectManagementAssistant:
    def __init__(self):
        self.projects = {}

    def add_project(self, project_name, deadline, resources):
        """
        Add a new project.
        :param project_name: Name of the project
        :param deadline: Deadline for the project (datetime object)
        :param resources: List of resources allocated to the project
        """
        self.projects[project_name] = {
            'deadline': deadline,
            'resources': resources,
            'tasks': []
        }
        logging.info(f"Project '{project_name}' added with deadline {deadline}.")

    def add_task_to_project(self, project_name, task_name, task_deadline):
        """
        Add a task to an existing project.
        :param project_name: Name of the project
        :param task_name: Name of the task
        :param task_deadline: Deadline for the task (datetime object)
        """
        if project_name in self.projects:
            self.projects[project_name]['tasks'].append({
                'name': task_name,
                'deadline': task_deadline
            })
            logging.info(f"Task '{task_name}' added to project '{project_name}' with deadline {task_deadline}.")
        else:
            logging.error(f"Project '{project_name}' not found.")

    def get_project_status(self, project_name):
        """
        Get the status of a project.
        :param project_name: Name of the project
        """
        if project_name in self.projects:
            project = self.projects[project_name]
            open_tasks = [task for task in project['tasks'] if datetime.now() < task['deadline']]
            status = {
                'total_tasks': len(project['tasks']),
                'open_tasks': len(open_tasks),
                'deadline': project['deadline']
            }
            return status
        else:
            logging.error(f"Project '{project_name}' not found.")
            return None

    def check_deadlines(self):
        """
        Check all projects for upcoming deadlines and emit alerts as necessary.
        """
        now = datetime.now()
        for project_name, project in self.projects.items():
            if now >= project['deadline']:
                event_bus.emit('project_deadline_reached', {'project_name': project_name})
                logging.info(f"Deadline reached for project '{project_name}'.")
            for task in project['tasks']:
                if now >= task['deadline']:
                    event_bus.emit('task_deadline_reached', {'project_name': project_name, 'task_name': task['name']})
                    logging.info(f"Deadline reached for task '{task['name']}' in project '{project_name}'.")

# Event handlers
def handle_new_project(event_data):
    project_name = event_data.get('project_name')
    deadline_str = event_data.get('deadline')
    resources = event_data.get('resources', [])

    try:
        deadline_obj = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M')
        assistant.add_project(project_name, deadline_obj, resources)
    except ValueError:
        logging.error(f"Invalid date format for project '{project_name}'. Expected 'YYYY-MM-DD HH:MM'.")


def handle_new_task(event_data):
    project_name = event_data.get('project_name')
    task_name = event_data.get('task_name')
    task_deadline_str = event_data.get('task_deadline')

    try:
        task_deadline_obj = datetime.strptime(task_deadline_str, '%Y-%m-%d %H:%M')
        assistant.add_task_to_project(project_name, task_name, task_deadline_obj)
    except ValueError:
        logging.error(f"Invalid date format for task '{task_name}' in project '{project_name}'. Expected 'YYYY-MM-DD HH:MM'.")


# Start module function
def start_module(event_bus):
    configure_logging()
    global assistant
    assistant = ProjectManagementAssistant()
    event_bus.subscribe('new_project', handle_new_project)
    event_bus.subscribe('new_task', handle_new_task)
    logging.info("ProjectManagementAssistant module started.")
