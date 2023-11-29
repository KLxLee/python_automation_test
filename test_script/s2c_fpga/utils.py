from threading import Thread
import subprocess, time, sys, platform, os
from functools import wraps

class Decorator:
    def logit(func):
        @wraps(func)
        def with_logging(*args, **kwargs):
            #print(f'[LOG] {func.__name__}({args}, {kwargs})')
            return func(*args, **kwargs)
        return with_logging

class Util:
    SUCCESS=0
    FAILURE=1
    TIMEOUT=2

    def append_env(name, value):
        env_sep = ';' if platform.system()=='Windows' else ':'
        #print(f'old [{name}]:{os.environ[name]}')
        os.environ[name] += env_sep + value
        #print(f'new [{name}]:{os.environ[name]}')

    def cat(path):
        with open(path, 'r') as f:
            print(f.read())

    def call(exec, args, timeout=None):
        args.insert(0, exec)
        process = subprocess.Popen(args=args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        def run(process, args):
            while process.poll() is None:
                line = process.stdout.readline()
                try:
                    line = line.strip().decode('ansi')
                except:
                    line = line.strip().decode('utf-8')
                print(f'{args}#{line}')
        daemon = False if timeout is None else True
        t = Thread(target=run, args=(process, args), daemon=daemon)
        t.start()
        if daemon:
            t.join(timeout)
            # kill the process if timeout
            if process.poll() is None:
                process.kill()
                return Util.TIMEOUT
            return Util.SUCCESS if process.returncode==0 else Util.FAILURE
        return process

if __name__ == '__main__':
    if platform.system()=='Windows':
        ret = Util.call(exec='ping', args=['-t','localhost'], timeout=5)
    else:
        ret = Util.call(exec='ping', args=['localhost'], timeout=5)
    print(f'ret: {ret}')
