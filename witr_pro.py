#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Witr Pro - 高级进程监控工具
Why is this running? Pro Edition

一个功能强大的进程监控工具，帮助开发者快速了解系统中运行的进程信息，
包括进程树可视化、资源占用监控、历史记录等功能。
"""

import sys
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

import psutil
import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.align import Align


console = Console()


@dataclass
class ProcessInfo:
    """进程信息数据类"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    create_time: str
    exe: str
    cmdline: str
    username: str
    ppid: int
    children_count: int
    connections: int
    threads: int


class ProcessMonitor:
    """进程监控核心类"""

    HISTORY_FILE = os.path.expanduser("~/.witr_pro_history.json")
    MAX_HISTORY = 100

    def __init__(self):
        self.history: List[Dict] = []
        self.load_history()

    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def save_history(self):
        """保存历史记录"""
        try:
            with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history[-self.MAX_HISTORY:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[yellow]警告: 无法保存历史记录: {e}[/yellow]")

    def add_to_history(self, query: str, result_count: int):
        """添加查询到历史记录"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "result_count": result_count
        }
        self.history.append(entry)
        self.save_history()

    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """获取单个进程信息"""
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                create_time = datetime.fromtimestamp(
                    proc.create_time()
                ).strftime("%Y-%m-%d %H:%M:%S")

                cmdline = " ".join(proc.cmdline()) if proc.cmdline() else ""
                if len(cmdline) > 100:
                    cmdline = cmdline[:97] + "..."

                exe = proc.exe() if hasattr(proc, 'exe') else ""

                return ProcessInfo(
                    pid=pid,
                    name=proc.name(),
                    status=proc.status(),
                    cpu_percent=proc.cpu_percent(interval=0.1),
                    memory_percent=proc.memory_percent(),
                    memory_mb=proc.memory_info().rss / 1024 / 1024,
                    create_time=create_time,
                    exe=exe,
                    cmdline=cmdline,
                    username=proc.username() if hasattr(proc, 'username') else "",
                    ppid=proc.ppid(),
                    children_count=len(proc.children()),
                    connections=len(proc.connections()) if hasattr(proc, 'connections') else 0,
                    threads=proc.num_threads()
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    def find_processes(self, keyword: str) -> List[ProcessInfo]:
        """根据关键词查找进程"""
        results = []
        keyword_lower = keyword.lower()

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']

                # 匹配进程名或PID
                if (keyword_lower in name.lower() or
                    keyword == str(pid) or
                    keyword in str(pid)):

                    info = self.get_process_info(pid)
                    if info:
                        results.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 按CPU使用率排序
        results.sort(key=lambda x: x.cpu_percent, reverse=True)
        return results

    def get_process_tree(self, pid: int) -> Optional[Tree]:
        """获取进程树"""
        try:
            proc = psutil.Process(pid)
            root = Tree(f"[bold cyan]{proc.name()}[/bold cyan] (PID: {pid})")
            self._build_tree(proc, root)
            return root
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def _build_tree(self, proc: psutil.Process, tree: Tree):
        """递归构建进程树"""
        try:
            children = proc.children()
            for child in children:
                try:
                    child_info = f"{child.name()} (PID: {child.pid})"
                    branch = tree.add(f"[green]{child_info}[/green]")
                    self._build_tree(child, branch)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def get_system_overview(self) -> Dict:
        """获取系统概览信息"""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu_percent': cpu_percent,
            'cpu_count': psutil.cpu_count(),
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / 1024 / 1024 / 1024,
            'memory_total_gb': memory.total / 1024 / 1024 / 1024,
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / 1024 / 1024 / 1024,
            'disk_total_gb': disk.total / 1024 / 1024 / 1024,
            'boot_time': datetime.fromtimestamp(
                psutil.boot_time()
            ).strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_top_processes(self, n: int = 10, sort_by: str = 'cpu') -> List[ProcessInfo]:
        """获取资源占用最高的进程"""
        processes = []

        for proc in psutil.process_iter(['pid']):
            try:
                info = self.get_process_info(proc.info['pid'])
                if info:
                    processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if sort_by == 'cpu':
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        elif sort_by == 'memory':
            processes.sort(key=lambda x: x.memory_percent, reverse=True)

        return processes[:n]


class DisplayManager:
    """显示管理类"""

    @staticmethod
    def create_process_table(processes: List[ProcessInfo], title: str = "进程列表") -> Table:
        """创建进程表格"""
        table = Table(
            title=title,
            title_style="bold magenta",
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("PID", style="dim", width=8)
        table.add_column("名称", style="bold green", width=20)
        table.add_column("状态", width=10)
        table.add_column("CPU%", justify="right", width=8)
        table.add_column("内存%", justify="right", width=8)
        table.add_column("内存(MB)", justify="right", width=10)
        table.add_column("启动时间", width=19)
        table.add_column("命令行", width=40, no_wrap=True)

        for proc in processes:
            cpu_style = "red" if proc.cpu_percent > 50 else "yellow" if proc.cpu_percent > 10 else "green"
            mem_style = "red" if proc.memory_percent > 10 else "yellow" if proc.memory_percent > 5 else "green"

            table.add_row(
                str(proc.pid),
                proc.name[:18],
                proc.status,
                f"[{cpu_style}]{proc.cpu_percent:.1f}%[/{cpu_style}]",
                f"[{mem_style}]{proc.memory_percent:.2f}%[/{mem_style}]",
                f"{proc.memory_mb:.1f}",
                proc.create_time,
                proc.cmdline[:37] + "..." if len(proc.cmdline) > 40 else proc.cmdline
            )

        return table

    @staticmethod
    def create_system_panel(info: Dict) -> Panel:
        """创建系统信息面板"""
        content = f"""
[bold]CPU:[/bold] {info['cpu_percent']:.1f}% ({info['cpu_count']} 核心)
[bold]内存:[/bold] {info['memory_percent']:.1f}% ({info['memory_used_gb']:.1f}GB / {info['memory_total_gb']:.1f}GB)
[bold]磁盘:[/bold] {info['disk_percent']:.1f}% ({info['disk_used_gb']:.1f}GB / {info['disk_total_gb']:.1f}GB)
[bold]启动时间:[/bold] {info['boot_time']}
        """.strip()

        return Panel(
            content,
            title="[bold blue]系统概览[/bold blue]",
            border_style="blue"
        )

    @staticmethod
    def create_process_detail_panel(proc: ProcessInfo) -> Panel:
        """创建进程详情面板"""
        content = f"""
[bold]PID:[/bold] {proc.pid}
[bold]名称:[/bold] {proc.name}
[bold]状态:[/bold] {proc.status}
[bold]CPU使用率:[/bold] {proc.cpu_percent:.1f}%
[bold]内存使用率:[/bold] {proc.memory_percent:.2f}%
[bold]内存使用:[/bold] {proc.memory_mb:.1f} MB
[bold]启动时间:[/bold] {proc.create_time}
[bold]可执行文件:[/bold] {proc.exe or 'N/A'}
[bold]命令行:[/bold] {proc.cmdline or 'N/A'}
[bold]用户名:[/bold] {proc.username or 'N/A'}
[bold]父进程PID:[/bold] {proc.ppid}
[bold]子进程数:[/bold] {proc.children_count}
[bold]网络连接数:[/bold] {proc.connections}
[bold]线程数:[/bold] {proc.threads}
        """.strip()

        return Panel(
            content,
            title=f"[bold cyan]进程详情 - {proc.name}[/bold cyan]",
            border_style="cyan"
        )


@click.group()
@click.version_option(version="1.0.0", prog_name="witr-pro")
def cli():
    """
    Witr Pro - 高级进程监控工具

    帮助开发者快速了解"为什么这个程序在运行"，提供进程查询、
    资源监控、进程树可视化等功能。
    """
    pass


@cli.command()
@click.argument('keyword')
@click.option('--tree', '-t', is_flag=True, help='显示进程树')
@click.option('--detail', '-d', is_flag=True, help='显示详细信息')
def find(keyword: str, tree: bool, detail: bool):
    """根据关键词查找进程"""
    monitor = ProcessMonitor()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]正在搜索进程...", total=None)
        processes = monitor.find_processes(keyword)
        progress.update(task, completed=True)

    if not processes:
        console.print(f"[yellow]未找到包含 '{keyword}' 的进程[/yellow]")
        return

    monitor.add_to_history(keyword, len(processes))

    console.print(f"\n[green]找到 {len(processes)} 个匹配的进程[/green]\n")

    if detail and len(processes) == 1:
        # 显示详细信息
        panel = DisplayManager.create_process_detail_panel(processes[0])
        console.print(panel)

        if tree:
            console.print()
            proc_tree = monitor.get_process_tree(processes[0].pid)
            if proc_tree:
                console.print(Panel(proc_tree, title="[bold green]进程树[/bold green]", border_style="green"))
    else:
        # 显示表格
        table = DisplayManager.create_process_table(processes, f"搜索结果: '{keyword}'")
        console.print(table)

        if tree and len(processes) <= 5:
            for proc in processes:
                console.print()
                proc_tree = monitor.get_process_tree(proc.pid)
                if proc_tree:
                    console.print(Panel(
                        proc_tree,
                        title=f"[bold green]{proc.name} (PID: {proc.pid}) 进程树[/bold green]",
                        border_style="green"
                    ))


@cli.command()
@click.option('--sort', '-s', type=click.Choice(['cpu', 'memory']), default='cpu',
              help='排序方式')
@click.option('--count', '-n', default=10, help='显示进程数量')
def top(sort: str, count: int):
    """显示资源占用最高的进程"""
    monitor = ProcessMonitor()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]正在收集进程信息...", total=None)
        processes = monitor.get_top_processes(count, sort)
        progress.update(task, completed=True)

    sort_name = "CPU" if sort == 'cpu' else "内存"
    table = DisplayManager.create_process_table(processes, f"按{sort_name}使用率排序 (Top {count})")
    console.print(table)


@cli.command()
@click.option('--refresh', '-r', default=2, help='刷新间隔(秒)')
@click.option('--sort', '-s', type=click.Choice(['cpu', 'memory']), default='cpu',
              help='排序方式')
def watch(refresh: int, sort: str):
    """实时监控进程资源占用"""
    monitor = ProcessMonitor()

    console.print(f"[cyan]开始实时监控，按 Ctrl+C 停止 (刷新间隔: {refresh}秒)[/cyan]\n")

    try:
        while True:
            processes = monitor.get_top_processes(15, sort)
            system_info = monitor.get_system_overview()

            layout = Layout()
            layout.split_column(
                Layout(name="system", size=7),
                Layout(name="processes")
            )

            layout["system"].update(DisplayManager.create_system_panel(system_info))

            sort_name = "CPU" if sort == 'cpu' else "内存"
            table = DisplayManager.create_process_table(
                processes,
                f"实时进程监控 - 按{sort_name}排序 (Top 15)"
            )
            layout["processes"].update(table)

            console.clear()
            console.print(layout)

            time.sleep(refresh)
    except KeyboardInterrupt:
        console.print("\n[yellow]监控已停止[/yellow]")


@cli.command()
def system():
    """显示系统概览"""
    monitor = ProcessMonitor()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]正在收集系统信息...", total=None)
        info = monitor.get_system_overview()
        progress.update(task, completed=True)

    panel = DisplayManager.create_system_panel(info)
    console.print(panel)

    # 额外信息
    console.print("\n[bold cyan]进程统计:[/bold cyan]")
    process_count = len(list(psutil.process_iter()))
    console.print(f"  总进程数: {process_count}")

    # 网络连接统计
    try:
        connections = psutil.net_connections()
        console.print(f"  网络连接数: {len(connections)}")
    except psutil.AccessDenied:
        console.print("  网络连接数: 需要管理员权限")


@cli.command()
def history():
    """显示查询历史"""
    monitor = ProcessMonitor()

    if not monitor.history:
        console.print("[yellow]暂无查询历史[/yellow]")
        return

    table = Table(
        title="[bold magenta]查询历史[/bold magenta]",
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("时间", width=20)
    table.add_column("查询关键词", style="green")
    table.add_column("结果数", justify="right", width=10)

    for entry in reversed(monitor.history[-20:]):
        table.add_row(
            entry['timestamp'][:19].replace('T', ' '),
            entry['query'],
            str(entry['result_count'])
        )

    console.print(table)


@cli.command()
@click.argument('pid', type=int)
def kill(pid: int):
    """终止指定进程"""
    try:
        proc = psutil.Process(pid)
        name = proc.name()

        if click.confirm(f"确定要终止进程 '{name}' (PID: {pid}) 吗?"):
            proc.terminate()
            try:
                proc.wait(timeout=3)
                console.print(f"[green]进程 '{name}' (PID: {pid}) 已终止[/green]")
            except psutil.TimeoutExpired:
                if click.confirm("进程未响应，是否强制结束?"):
                    proc.kill()
                    console.print(f"[green]进程 '{name}' (PID: {pid}) 已被强制结束[/green]")
    except psutil.NoSuchProcess:
        console.print(f"[red]进程 PID {pid} 不存在[/red]")
    except psutil.AccessDenied:
        console.print(f"[red]权限不足，无法终止进程 PID {pid}[/red]")


@cli.command()
def info():
    """显示工具信息"""
    banner = """
[bold cyan]
██╗    ██╗██╗████████╗██████╗     ██████╗ ██████╗  ██████╗
██║    ██║██║╚══██╔══╝██╔══██╗    ██╔══██╗██╔══██╗██╔═══██╗
██║ █╗ ██║██║   ██║   ██████╔╝    ██████╔╝██████╔╝██║   ██║
██║███╗██║██║   ██║   ██╔══██╗    ██╔═══╝ ██╔══██╗██║   ██║
╚███╔███╔╝██║   ██║   ██║  ██║    ██║     ██║  ██║╚██████╔╝
 ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝
[/bold cyan]
[bold magenta]              Why is this running? Pro Edition[/bold magenta]
    """
    console.print(banner)

    info_panel = Panel(
        """
[bold]版本:[/bold] 1.0.0
[bold]作者:[/bold] Witr Pro Team
[bold]许可证:[/bold] MIT
[bold]GitHub:[/bold] https://github.com/yourusername/witr-pro

[bold]功能特性:[/bold]
  • 进程搜索与查询
  • 实时资源监控
  • 进程树可视化
  • 系统概览
  • 查询历史记录
  • 进程终止

[bold]使用帮助:[/bold]
  witr-pro --help
        """.strip(),
        title="[bold green]关于 Witr Pro[/bold green]",
        border_style="green"
    )
    console.print(info_panel)


if __name__ == '__main__':
    cli()
