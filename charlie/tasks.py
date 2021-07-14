from dataclasses import dataclass

@dataclass
class Task:
    name: str
    command: str
    workdir: str = "."
    shell: str = ""

    @classmethod
    def from_config(cls, cfg):
        tasks = []
        for section in cfg.sections():
            if section.startswith('job.'):
                data = {**cfg[section]}
                data.setdefault('name', cfg[section].get('name', section[4:]))
                t = Task(**data)
                tasks.append(t)
        return tasks
    
    def get_shell_command(self):
        if self.shell == 'wsl':
            return f'bash -c "{self.command}"'
        elif self.shell == 'powershell':
            return f'powershell "{self.command}"'
        else:
            return self.command