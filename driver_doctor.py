#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
驱动检测与修复工具 v1.3
- 全平台支持：Dell / Lenovo / ASUS / MSI / 技嘉 / HP / 宏碁
             华为 / 小米 / 三星 / 东芝 / 七彩虹 / 映泰 / 华南杂牌 等
- 白天 / 夜间主题
- 实时下载 & 安装进度
- GPU 信息检测（NVIDIA / AMD / Intel）
"""

import sys
import os
import subprocess
import json
import threading
import ctypes
import time
import datetime
import tempfile
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ─── 错误码 ────────────────────────────────────────────────────────────────────

ERROR_CODES = {
    1:  ("配置不正确",       "reinstall"),
    2:  ("驱动加载失败",     "reinstall"),
    3:  ("驱动损坏或缺失",   "reinstall"),
    10: ("设备无法启动",     "reinstall"),
    12: ("资源不足",         "update"),
    14: ("需要重启生效",     "reboot"),
    18: ("需要重新安装驱动", "reinstall"),
    19: ("注册表损坏",       "reinstall"),
    22: ("设备被禁用",       "enable"),
    24: ("设备未连接",       "check"),
    28: ("未安装驱动",       "reinstall"),
    31: ("设备工作异常",     "reinstall"),
    32: ("服务已禁用",       "reinstall"),
    33: ("资源被占用",       "reboot"),
    37: ("驱动返回失败",     "reinstall"),
    38: ("驱动冲突需重启",   "reboot"),
    39: ("驱动文件损坏",     "reinstall"),
    40: ("注册表键值丢失",   "reinstall"),
    43: ("设备报告问题",     "reinstall"),
    45: ("设备已断开",       "check"),
    48: ("驱动被系统屏蔽",   "update"),
    52: ("驱动签名无效",     "update"),
}

ACTION_LABELS = {
    "reinstall": "重新安装",
    "update":    "更新驱动",
    "enable":    "启用设备",
    "reboot":    "需要重启",
    "check":     "检查硬件",
}

# ─── 主题 ──────────────────────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "BG": "#1a1a2e", "BG2": "#16213e", "BG3": "#0f3460",
        "FG": "#e0e0e0", "FG2": "#8899aa",
        "GREEN": "#00d4aa", "RED": "#ff4757", "YELLOW": "#ffa502", "BLUE": "#70a1ff",
        "SEP": "#0f3460", "BTN_DIS": "#252540", "FG_DIS": "#555566",
        "ICON": "🌙", "LABEL": "夜间模式",
    },
    "light": {
        "BG": "#f0f2f5", "BG2": "#ffffff", "BG3": "#dde3ee",
        "FG": "#1e272e", "FG2": "#576574",
        "GREEN": "#00957a", "RED": "#c0392b", "YELLOW": "#d35400", "BLUE": "#2980b9",
        "SEP": "#c8d0db", "BTN_DIS": "#c8d0db", "FG_DIS": "#a0a8b0",
        "ICON": "☀", "LABEL": "白天模式",
    },
}

# ─── 品牌配置 ──────────────────────────────────────────────────────────────────

# Dell Command Update CLI 可能的安装路径
DELL_DCU_PATHS = [
    r"C:\Program Files\Dell\CommandUpdate\dcu-cli.exe",
    r"C:\Program Files (x86)\Dell\CommandUpdate\dcu-cli.exe",
]

# Lenovo System Update 可能的安装路径
LENOVO_LSU_PATHS = [
    r"C:\Program Files (x86)\Lenovo\System Update\tvsukernel.exe",
    r"C:\Program Files\Lenovo\System Update\tvsukernel.exe",
]

# Dell Command Update 下载页
DELL_DCU_URL = "https://www.dell.com/support/kbdoc/zh-cn/000177325"
# Lenovo System Update 下载页
LENOVO_LSU_URL = "https://support.lenovo.com/us/zh/solutions/ht003029"

# ── 全平台品牌识别关键词（manufacturer 字符串小写匹配）──────────────────────
BRAND_KEYWORDS = {
    "Dell":      ["dell"],
    "Lenovo":    ["lenovo", "ibm"],
    "ASUS":      ["asus", "asustek"],
    "MSI":       ["micro-star", "msi"],
    "Gigabyte":  ["gigabyte"],
    "HP":        ["hewlett-packard", "hp ", "hp,"],
    "Acer":      ["acer"],
    "Huawei":    ["huawei"],
    "Xiaomi":    ["xiaomi"],
    "Samsung":   ["samsung"],
    "Toshiba":   ["toshiba"],
    "Sony":      ["sony"],
    "Colorful":  ["colorful"],
    "Biostar":   ["biostar"],
    "EVGA":      ["evga"],
    "Supermicro":["supermicro"],
    "Huanan":    ["huanan", "jingsha", "kllisre", "machinist",
                  "atermiter", "x99", "x79", "b85", "h81", "华南"],
}

# ── 各品牌官方驱动工具名称、下载 URL ────────────────────────────────────────
BRAND_TOOL_INFO = {
    "Dell":      ("Dell Command Update",       "https://www.dell.com/support/kbdoc/zh-cn/000177325"),
    "Lenovo":    ("Lenovo System Update",      "https://support.lenovo.com/us/zh/solutions/ht003029"),
    "ASUS":      ("MyASUS / Live Update",      "https://www.asus.com/support/FAQ/1042459/"),
    "MSI":       ("MSI Center",                "https://www.msi.com/Landing/MSI-Center"),
    "Gigabyte":  ("Gigabyte APP Center",       "https://www.gigabyte.com/Support/Utility"),
    "HP":        ("HP Support Assistant",      "https://support.hp.com/cn-zh/help/hp-support-assistant"),
    "Acer":      ("Acer Care Center",          "https://www.acer.com/ac/zh/CN/content/drivers"),
    "Huawei":    ("华为电脑管家",               "https://consumer.huawei.com/cn/support/content/zh-cn00853387/"),
    "Xiaomi":    ("小米电脑管家",               "https://www.mi.com/service/computer"),
    "Samsung":   ("Samsung Update",            "https://www.samsung.com/cn/support/model/update/"),
    "Toshiba":   ("Toshiba Service Station",   "https://support.dynabook.com/"),
    "Sony":      ("Sony Update Essentials",    "https://www.sony.com.cn/support/"),
    "Colorful":  ("七彩虹官网驱动",             "https://www.colorful.cn/service_support_driver_1.aspx"),
    "Biostar":   ("Biostar 官网驱动",           "https://www.biostar.com.tw/app/en/support/"),
    "EVGA":      ("EVGA 官网驱动",             "https://www.evga.com/support/download/"),
    "Supermicro":("Supermicro 驱动页",         "https://www.supermicro.com/en/support/resources/downloadcenter/"),
    "Huanan":    (None,                        None),   # 无官方工具，特殊处理
}

# ── 品牌显示颜色（十六进制）────────────────────────────────────────────────
BRAND_COLORS = {
    "Dell":      "#00a8e0",
    "Lenovo":    "#e2231a",
    "ASUS":      "#00539b",
    "MSI":       "#d4001a",
    "Gigabyte":  "#ee7203",
    "HP":        "#0096d6",
    "Acer":      "#83b81a",
    "Huawei":    "#cf0a2c",
    "Xiaomi":    "#ff6900",
    "Samsung":   "#1428a0",
    "Toshiba":   "#cc0000",
    "Sony":      "#000000",
    "Colorful":  "#e63312",
    "Biostar":   "#0055a5",
    "EVGA":      "#333333",
    "Supermicro":"#005baa",
    "Huanan":    "#b8860b",
    "Other":     "#4a90d9",
}

# Dell DCU /applyUpdates 返回码
DELL_RC = {
    0: ("成功，无需重启",   True,  False),
    1: ("成功，需要重启",   True,  True),
    2: ("部分更新失败",     True,  False),
    3: ("需先重启再继续",   False, True),
    4: ("未配置",           False, False),
    5: ("目录下载失败",     False, False),
    6: ("目录签名无效",     False, False),
    7: ("目录内容无效",     False, False),
    8: ("系统不兼容",       False, False),
    9: ("驱动处理失败",     False, False),
}

# ─── 管理员权限 ────────────────────────────────────────────────────────────────

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)

# ─── 系统命令 ──────────────────────────────────────────────────────────────────

def run_ps(script, timeout=60):
    cmd = ["powershell", "-NoProfile", "-NonInteractive",
           "-ExecutionPolicy", "Bypass", "-Command", script]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "执行超时", -1
    except Exception as e:
        return "", str(e), -1


def run_cmd(args, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        out = r.stdout.decode("utf-8", errors="replace").strip()
        err = r.stderr.decode("utf-8", errors="replace").strip()
        return out, err, r.returncode
    except subprocess.TimeoutExpired:
        return "", "执行超时", -1
    except Exception as e:
        return "", str(e), -1

# ─── 系统信息检测 ──────────────────────────────────────────────────────────────

def detect_system_info():
    """
    检测品牌、型号、序列号、GPU。
    返回 {brand, model, serial, raw_mfr, gpu_vendor, gpu_name}
    brand: "Dell"|"Lenovo"|"ASUS"|"MSI"|"Gigabyte"|"HP"|"Acer"|
           "Huawei"|"Xiaomi"|"Samsung"|"Toshiba"|"Sony"|
           "Colorful"|"Biostar"|"EVGA"|"Supermicro"|"Huanan"|"Other"
    """
    ps = r"""
$cs   = Get-WmiObject Win32_ComputerSystem
$bios = Get-WmiObject Win32_BIOS
$gpu  = Get-WmiObject Win32_VideoController | Select-Object -First 1
[PSCustomObject]@{
    manufacturer = $cs.Manufacturer
    model        = $cs.Model
    serial       = $bios.SerialNumber
    gpu_name     = $gpu.Name
    gpu_driver   = $gpu.DriverVersion
} | ConvertTo-Json
"""
    stdout, _, _ = run_ps(ps, timeout=15)
    info = {
        "brand": "Other", "model": "未知", "serial": "未知",
        "raw_mfr": "", "gpu_vendor": "Unknown", "gpu_name": "未知",
    }
    if not stdout:
        return info
    try:
        d = json.loads(stdout)
        mfr = (d.get("manufacturer") or "").strip()
        info["raw_mfr"] = mfr
        info["model"]   = (d.get("model")  or "未知").strip()
        info["serial"]  = (d.get("serial") or "未知").strip()
        gpu_name = (d.get("gpu_name") or "").strip()
        info["gpu_name"] = gpu_name or "未知"
        gpu_low = gpu_name.lower()
        if "nvidia" in gpu_low or "geforce" in gpu_low or "quadro" in gpu_low or "rtx" in gpu_low or "gtx" in gpu_low:
            info["gpu_vendor"] = "NVIDIA"
        elif "amd" in gpu_low or "radeon" in gpu_low or "rx " in gpu_low:
            info["gpu_vendor"] = "AMD"
        elif "intel" in gpu_low or "iris" in gpu_low or "uhd" in gpu_low or "hd graphics" in gpu_low:
            info["gpu_vendor"] = "Intel"

        # 品牌识别：逐品牌匹配关键词
        mfr_low = mfr.lower()
        matched = "Other"
        for brand, keywords in BRAND_KEYWORDS.items():
            if any(kw in mfr_low for kw in keywords):
                matched = brand
                break
        info["brand"] = matched
    except (json.JSONDecodeError, TypeError):
        pass
    return info

# ─── Dell Command Update ───────────────────────────────────────────────────────

def find_dell_dcu():
    """返回 dcu-cli.exe 路径，未找到返回 None"""
    for p in DELL_DCU_PATHS:
        if os.path.exists(p):
            return p
    # 从注册表查找
    ps = r"""
$keys = @(
    "HKLM:\SOFTWARE\Dell\UpdateService\Clients\CommandUpdate",
    "HKLM:\SOFTWARE\WOW6432Node\Dell\UpdateService\Clients\CommandUpdate"
)
foreach ($k in $keys) {
    if (Test-Path $k) {
        $dir = (Get-ItemProperty $k -ErrorAction SilentlyContinue).InstallDir
        if ($dir) {
            $exe = Join-Path $dir "dcu-cli.exe"
            if (Test-Path $exe) { Write-Output $exe; break }
        }
    }
}
"""
    out, _, _ = run_ps(ps, timeout=10)
    if out and os.path.exists(out):
        return out
    return None


def dell_scan_updates(dcu, log):
    """
    扫描 Dell 驱动更新。
    返回 (updates_count, update_titles[])
    rc=0: 无更新, rc=1: 有更新, rc>=500: 错误
    """
    log_dir = tempfile.mkdtemp(prefix="dcu_")
    log_file = os.path.join(log_dir, "scan.log")
    log("  Dell Command Update 正在扫描...")

    _, _, rc = run_cmd(
        [dcu, "/scan", f"-outputlog={log_file}", "-updateType=driver,firmware"],
        timeout=180,
    )

    titles = []
    if os.path.exists(log_file):
        try:
            content = open(log_file, encoding="utf-8", errors="replace").read()
            # DCU 日志含 "Package Name:" 行
            for line in content.splitlines():
                line = line.strip()
                if "Package Name:" in line or "packageid=" in line.lower():
                    name = line.split(":", 1)[-1].strip().strip('"')
                    if name:
                        titles.append(name)
        except Exception:
            pass

    if rc == 0:
        log("  没有可用的 Dell 驱动更新")
        return 0, []
    elif rc == 1:
        count = len(titles) if titles else 1
        log(f"  发现 {count} 个 Dell 驱动更新")
        return count, titles
    else:
        desc = {
            3: "请重启电脑后再扫描",
            4: "Dell Command Update 未完成初始化配置",
            5: "无法下载驱动目录，请检查网络",
            6: "目录签名验证失败",
        }.get(rc, f"扫描失败，错误码 {rc}")
        log(f"  ✗ {desc}")
        return -1, []


def dell_apply_updates(dcu, log, progress_cb):
    """
    安装 Dell 驱动更新（流式进度）。
    返回 (success, reboot_required)
    """
    log_dir  = tempfile.mkdtemp(prefix="dcu_")
    log_file = os.path.join(log_dir, "apply.log")

    progress_cb("download", 0, 1, "准备下载 Dell 驱动...")

    proc = subprocess.Popen(
        [dcu, "/applyUpdates", "-silent", "-reboot=disable",
         "-updateType=driver,firmware", f"-outputlog={log_file}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # 实时尾随日志文件解析进度
    seen_lines = set()
    dl_done    = False
    inst_pct   = 0

    while proc.poll() is None:
        time.sleep(1)
        if not os.path.exists(log_file):
            continue
        try:
            lines = open(log_file, encoding="utf-8", errors="replace").readlines()
        except Exception:
            continue
        for line in lines:
            line = line.strip()
            if not line or line in seen_lines:
                continue
            seen_lines.add(line)
            lo = line.lower()

            if any(k in lo for k in ("download", "downloading", "下载")):
                if not dl_done:
                    progress_cb("download", 0, 1, line[:60])
                log(f"  ↓ {line[:80]}")

            elif any(k in lo for k in ("installing", "install", "applying", "安装")):
                dl_done = True
                progress_cb("download", 1, 1, "")
                inst_pct = min(inst_pct + 10, 90)
                progress_cb("install", inst_pct, 100, line[:60])
                log(f"  ⚙ {line[:80]}")

            elif any(k in lo for k in ("success", "complete", "完成", "succeeded")):
                log(f"  ✓ {line[:80]}")

            elif any(k in lo for k in ("error", "fail", "failed", "错误")):
                log(f"  ✗ {line[:80]}")

    proc.wait()
    rc = proc.returncode

    msg, success, reboot = DELL_RC.get(rc, (f"未知结果 (rc={rc})", False, False))
    progress_cb("download", 1, 1, "")
    progress_cb("install", 100, 100, "")
    progress_cb("done", 0, 0, "")

    if success:
        log(f"  ✓ Dell 驱动更新完成：{msg}")
    else:
        log(f"  ✗ Dell 驱动更新失败：{msg}")
    return success, reboot

# ─── Lenovo System Update ──────────────────────────────────────────────────────

def find_lenovo_lsu():
    """返回 tvsukernel.exe 路径，未找到返回 None"""
    for p in LENOVO_LSU_PATHS:
        if os.path.exists(p):
            return p
    ps = r"""
$key = "HKLM:\SOFTWARE\WOW6432Node\Lenovo\System Update"
if (Test-Path $key) {
    $dir = (Get-ItemProperty $key -ErrorAction SilentlyContinue).Path
    if ($dir) {
        $exe = Join-Path $dir "tvsukernel.exe"
        if (Test-Path $exe) { Write-Output $exe }
    }
}
"""
    out, _, _ = run_ps(ps, timeout=10)
    if out and os.path.exists(out):
        return out
    return None


def lenovo_apply_updates(lsu, log, progress_cb):
    """
    通过 Lenovo System Update CLI 安装驱动。
    返回 (success, reboot_required)
    """
    log("  Lenovo System Update 正在搜索并安装驱动...")
    progress_cb("download", 0, 1, "正在连接 Lenovo 驱动服务器...")

    lsu_dir = os.path.dirname(lsu)

    # LSU CLI 参数：静默模式，搜索所有，安装，允许需要重启的包，不自动重启
    cmd = [
        lsu,
        "/CM",
        "-search", "A",
        "-action", "INSTALL",
        "-includerebootpackages", "1,3",
        "-noreboot",
        "-noicon",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="gbk", errors="replace",
            cwd=lsu_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        log(f"  ✗ 无法启动 Lenovo System Update: {e}")
        return False, False

    reboot_required = False
    pkg_total       = 0
    pkg_done        = 0
    dl_done         = False

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        lo = line.lower()

        if "package" in lo and ("found" in lo or "total" in lo):
            try:
                n = int("".join(filter(str.isdigit, line)))
                if n > 0:
                    pkg_total = n
                    log(f"  找到 {n} 个 Lenovo 驱动包")
                    progress_cb("download", 0, pkg_total, "")
            except ValueError:
                pass

        elif any(k in lo for k in ("downloading", "download")):
            pkg_done = min(pkg_done + 1, max(pkg_total, 1))
            progress_cb("download", pkg_done, max(pkg_total, 1), line[:60])
            log(f"  ↓ {line[:80]}")

        elif any(k in lo for k in ("installing", "install")):
            dl_done = True
            progress_cb("download", max(pkg_total, 1), max(pkg_total, 1), "")
            pkg_done = min(pkg_done + 1, max(pkg_total, 1))
            progress_cb("install", pkg_done, max(pkg_total, 1), line[:60])
            log(f"  ⚙ {line[:80]}")

        elif "reboot" in lo or "restart" in lo:
            reboot_required = True
            log(f"  ⚠ {line[:80]}")

        elif any(k in lo for k in ("success", "complete", "finish")):
            log(f"  ✓ {line[:80]}")

        elif any(k in lo for k in ("error", "fail", "failed")):
            log(f"  ✗ {line[:80]}")

    proc.wait()
    rc = proc.returncode

    progress_cb("download", max(pkg_total, 1), max(pkg_total, 1), "")
    progress_cb("install",  max(pkg_total, 1), max(pkg_total, 1), "")
    progress_cb("done", 0, 0, "")

    # LSU rc: 0=success, 1=reboot needed, others=error
    if rc in (0, 1):
        reboot_required = reboot_required or (rc == 1)
        log("  ✓ Lenovo 驱动更新完成")
        return True, reboot_required
    else:
        log(f"  ✗ Lenovo 驱动更新失败，错误码 {rc}")
        return False, reboot_required

# ─── Windows Update 通用回退 ───────────────────────────────────────────────────

def search_driver_updates_wua(log):
    log("  通过 Windows Update 搜索驱动...")
    ps = r"""
try {
    $Session  = New-Object -ComObject Microsoft.Update.Session
    $Searcher = $Session.CreateUpdateSearcher()
    $Results  = $Searcher.Search("IsInstalled=0 AND Type='Driver'")
    $list = @()
    foreach ($u in $Results.Updates) {
        $list += [PSCustomObject]@{ title=$u.Title; size=[math]::Round($u.MaxDownloadSize/1MB,1) }
    }
    if ($list.Count -gt 0) { $list | ConvertTo-Json -Depth 3 } else { Write-Output "[]" }
} catch { Write-Error $_.Exception.Message }
"""
    stdout, stderr, _ = run_ps(ps, timeout=120)
    updates = []
    if not stdout or stdout == "[]":
        if stderr:
            log(f"  Windows Update 搜索失败: {stderr[:200]}")
        else:
            log("  未找到可用的驱动更新")
        return updates
    try:
        raw = json.loads(stdout)
        if isinstance(raw, dict):
            raw = [raw]
        for u in raw:
            updates.append({"title": u.get("title", ""), "size": u.get("size", 0)})
    except (json.JSONDecodeError, TypeError):
        pass
    return updates


def install_driver_updates_wua(log, progress_cb):
    ps = r"""
$ErrorActionPreference='Stop'
try {
    $Session  = New-Object -ComObject Microsoft.Update.Session
    $Searcher = $Session.CreateUpdateSearcher()
    $Results  = $Searcher.Search("IsInstalled=0 AND Type='Driver'")
    $Total    = $Results.Updates.Count
    if ($Total -eq 0) { Write-Output "NO_UPDATES"; exit }
    Write-Output "FOUND:$Total"; [Console]::Out.Flush()
    $reboot = $false
    for ($i=0; $i -lt $Total; $i++) {
        $u=$Results.Updates[$i]; $safe=$u.Title -replace '[^\x20-\x7E]','?'
        Write-Output "DL_START:$($i+1):$Total:$safe"; [Console]::Out.Flush()
        $col=New-Object -ComObject Microsoft.Update.UpdateColl; $col.Add($u)|Out-Null
        $dl=$Session.CreateUpdateDownloader(); $dl.Updates=$col; $dl.Download()|Out-Null
        Write-Output "DL_DONE:$($i+1):$Total"; [Console]::Out.Flush()
    }
    for ($i=0; $i -lt $Total; $i++) {
        $u=$Results.Updates[$i]; $safe=$u.Title -replace '[^\x20-\x7E]','?'
        Write-Output "INST_START:$($i+1):$Total:$safe"; [Console]::Out.Flush()
        $col=New-Object -ComObject Microsoft.Update.UpdateColl; $col.Add($u)|Out-Null
        $inst=New-Object -ComObject Microsoft.Update.Installer; $inst.Updates=$col
        $r=$inst.Install(); if ($r.RebootRequired){$reboot=$true}
        Write-Output "INST_DONE:$($i+1):$Total:$($r.ResultCode)"; [Console]::Out.Flush()
    }
    Write-Output "ALL_DONE:$reboot"
} catch { Write-Output "ERROR:$($_.Exception.Message)" }
"""
    cmd = ["powershell", "-NoProfile", "-NonInteractive",
           "-ExecutionPolicy", "Bypass", "-Command", ps]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace",
                                creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        log(f"  ✗ 无法启动 PowerShell: {e}")
        return False, False

    reboot_required = False
    success = False
    for raw_line in proc.stdout:
        line = raw_line.strip()
        if not line:
            continue
        if line == "NO_UPDATES":
            log("  没有可用的驱动更新")
            break
        elif line.startswith("FOUND:"):
            log(f"  找到 {line.split(':',1)[1]} 个驱动更新")
        elif line.startswith("DL_START:"):
            p = line.split(":", 3)
            cur, tot = int(p[1]), int(p[2])
            log(f"  ↓ 下载 {cur}/{tot}: {p[3] if len(p)>3 else ''}")
            progress_cb("download", cur-1, tot, "")
        elif line.startswith("DL_DONE:"):
            p = line.split(":")
            progress_cb("download", int(p[1]), int(p[2]), "")
        elif line.startswith("INST_START:"):
            p = line.split(":", 3)
            cur, tot = int(p[1]), int(p[2])
            log(f"  ⚙ 安装 {cur}/{tot}: {p[3] if len(p)>3 else ''}")
            progress_cb("install", cur-1, tot, "")
        elif line.startswith("INST_DONE:"):
            p = line.split(":")
            progress_cb("install", int(p[1]), int(p[2]), "")
        elif line.startswith("ALL_DONE:"):
            reboot_required = line.split(":",1)[1].strip().lower() == "true"
            success = True
            progress_cb("done", 0, 0, "")
            log("  ✓ Windows Update 驱动安装完成")
        elif line.startswith("ERROR:"):
            log(f"  ✗ {line.split(':',1)[1][:200]}")
    proc.wait()
    return success, reboot_required

# ─── 设备扫描 ──────────────────────────────────────────────────────────────────

def scan_devices():
    ps = r"""
$items = Get-WmiObject Win32_PnPEntity |
    Where-Object { $_.ConfigManagerErrorCode -ne 0 } |
    Select-Object Name, DeviceID, ConfigManagerErrorCode, DriverVersion
$out = @()
foreach ($d in $items) {
    $out += [PSCustomObject]@{
        name          = if ($d.Name)          { $d.Name }          else { "未知设备" }
        deviceId      = if ($d.DeviceID)      { $d.DeviceID }      else { "" }
        errorCode     = [int]$d.ConfigManagerErrorCode
        driverVersion = if ($d.DriverVersion) { $d.DriverVersion } else { "未知" }
    }
}
if ($out.Count -gt 0) { $out | ConvertTo-Json -Depth 3 } else { "[]" }
"""
    stdout, _, _ = run_ps(ps, timeout=40)
    devices = []
    if not stdout:
        return devices
    try:
        raw = json.loads(stdout)
        if isinstance(raw, dict):
            raw = [raw]
        for d in raw:
            code = int(d.get("errorCode", 0))
            desc, action = ERROR_CODES.get(code, (f"未知错误 (代码 {code})", "check"))
            devices.append({
                "name":          d.get("name", "未知设备"),
                "deviceId":      d.get("deviceId", ""),
                "errorCode":     code,
                "errorDesc":     desc,
                "action":        action,
                "driverVersion": d.get("driverVersion", "未知"),
            })
    except (json.JSONDecodeError, TypeError):
        pass
    return devices

# ─── 驱动修复 ──────────────────────────────────────────────────────────────────

def fix_device(device, log):
    dev_id = device["deviceId"].replace("'", "\\'")
    action = device["action"]
    code   = device["errorCode"]
    log(f"  处理: {device['name']}")

    if action == "enable":
        ps = f"""
$d = Get-WmiObject Win32_PnPEntity | Where-Object {{ $_.DeviceID -eq '{dev_id}' }}
if ($d) {{ $d.Enable() | Out-Null; Write-Output "OK" }} else {{ Write-Output "NOTFOUND" }}
"""
        out, err, _ = run_ps(ps, timeout=20)
        if "OK" in out:
            log("  ✓ 已重新启用设备")
            return True
        log(f"  ✗ 启用失败: {err or out}")
        return False

    elif action in ("reinstall", "install", "update"):
        log("  触发系统重新扫描设备...")
        run_cmd(["pnputil", "/scan-devices"], timeout=60)
        time.sleep(3)
        ps = f"""
$d = Get-WmiObject Win32_PnPEntity | Where-Object {{ $_.DeviceID -eq '{dev_id}' }}
if ($d) {{ Write-Output $d.ConfigManagerErrorCode }} else {{ Write-Output "404" }}
"""
        out2, _, _ = run_ps(ps, timeout=10)
        try:
            new_code = int(out2.strip())
            if new_code == 0:
                log("  ✓ 修复成功")
                return True
            elif new_code != code:
                log(f"  ~ 状态从 {code} 变为 {new_code}，可能需要重启")
            else:
                log("  ✗ 自动修复未成功，建议使用品牌工具更新驱动")
        except (ValueError, AttributeError):
            log("  ~ 无法验证修复结果")
        return False

    elif action == "reboot":
        log("  ⚠ 此设备需要重启计算机")
    elif action == "check":
        log("  ⚠ 请检查设备是否正确连接")
    else:
        log(f"  ~ 跳过 (action={action})")
    return False

# ─── GUI ───────────────────────────────────────────────────────────────────────

class App:

    def __init__(self, root):
        self.root        = root
        self.root.title("驱动检测与修复工具  v1.2")
        self.root.geometry("1000x720")
        self.root.minsize(760, 540)

        self.devices     = []
        self.running     = False
        self.reboot_flag = False
        self.theme_name  = "dark"
        self._tk_widgets = []

        # 系统信息（后台获取）
        self.sys_info    = {"brand": "检测中...", "model": "", "serial": ""}
        self.dcu_path    = None   # Dell Command Update CLI
        self.lsu_path    = None   # Lenovo System Update CLI

        self._apply_ttk_styles()
        self._build_ui()
        self._apply_theme()
        # 后台检测系统信息
        threading.Thread(target=self._detect_system_thread, daemon=True).start()

    # ── 主题 ──────────────────────────────────────────────────────────────────

    @property
    def T(self):
        return THEMES[self.theme_name]

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self._apply_ttk_styles()
        self._apply_theme()

    def _apply_ttk_styles(self):
        T = THEMES[self.theme_name]
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame",      background=T["BG"])
        s.configure("TLabel",      background=T["BG"],  foreground=T["FG"],    font=("微软雅黑", 9))
        s.configure("H1.TLabel",   background=T["BG"],  foreground=T["GREEN"], font=("微软雅黑", 14, "bold"))
        s.configure("Sub.TLabel",  background=T["BG"],  foreground=T["FG2"],   font=("微软雅黑", 8))
        s.configure("Brand.TLabel",background=T["BG"],  foreground=T["BLUE"],  font=("微软雅黑", 9, "bold"))
        s.configure("TButton",
            background=T["BG3"], foreground=T["FG"],
            font=("微软雅黑", 9, "bold"), relief="flat", padding=(12, 6))
        s.map("TButton",
            background=[("active", T["BLUE"]),    ("disabled", T["BTN_DIS"])],
            foreground=[("active", T["FG"]),      ("disabled", T["FG_DIS"])])
        s.configure("Accent.TButton",
            background=T["GREEN"], foreground="#000",
            font=("微软雅黑", 9, "bold"), relief="flat", padding=(14, 7))
        s.map("Accent.TButton",
            background=[("active", T["BLUE"]),    ("disabled", T["BTN_DIS"])],
            foreground=[("active", "#fff"),        ("disabled", T["FG_DIS"])])
        s.configure("Treeview",
            background=T["BG2"], foreground=T["FG"],
            fieldbackground=T["BG2"], rowheight=30, font=("微软雅黑", 9))
        s.configure("Treeview.Heading",
            background=T["BG3"], foreground=T["FG"],
            font=("微软雅黑", 9, "bold"), relief="flat")
        s.map("Treeview",
            background=[("selected", T["BG3"])],
            foreground=[("selected", T["GREEN"])])
        s.configure("TProgressbar",
            background=T["GREEN"], troughcolor=T["BG2"], thickness=6)
        s.configure("TSeparator", background=T["SEP"])
        s.configure("TPanedwindow", background=T["BG"])

    def _apply_theme(self):
        T = self.T
        self.root.configure(bg=T["BG"])
        for w, keys in self._tk_widgets:
            try:
                cfg = {}
                if "bg"  in keys: cfg["bg"]  = T[keys["bg"]]
                if "fg"  in keys: cfg["fg"]  = T[keys["fg"]]
                if "ibg" in keys: cfg["insertbackground"] = T[keys["ibg"]]
                w.configure(**cfg)
            except tk.TclError:
                pass
        if hasattr(self, "btn_theme"):
            T = self.T
            self.btn_theme.configure(text=f"  {T['ICON']}  {T['LABEL']}")
        if hasattr(self, "tree"):
            T = self.T
            self.tree.tag_configure("err",  foreground=T["RED"])
            self.tree.tag_configure("warn", foreground=T["YELLOW"])
            self.tree.tag_configure("ok",   foreground=T["GREEN"])

    def _reg(self, widget, **keys):
        self._tk_widgets.append((widget, keys))
        return widget

    # ── 界面构建 ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        T = self.T

        # ── 标题栏
        header = ttk.Frame(self.root, padding=(18, 10, 18, 6))
        header.pack(fill="x")
        ttk.Label(header, text="⚙  驱动检测与修复工具", style="H1.TLabel").pack(side="left")
        self.btn_theme = ttk.Button(header, text=f"  {T['ICON']}  {T['LABEL']}",
                                    command=self.toggle_theme)
        self.btn_theme.pack(side="right", padx=(8, 0))
        admin_txt   = "● 管理员模式" if is_admin() else "● 普通用户（修复受限）"
        admin_color = "GREEN" if is_admin() else "YELLOW"
        self._reg(tk.Label(header, text=admin_txt, font=("微软雅黑", 8)),
                  bg="BG", fg=admin_color).pack(side="right", padx=8)

        ttk.Separator(self.root).pack(fill="x")

        # ── 品牌信息栏
        brand_bar = self._reg(tk.Frame(self.root, pady=6), bg="BG2")
        brand_bar.pack(fill="x")

        self._reg(tk.Label(brand_bar, text="电脑品牌:", font=("微软雅黑", 9)),
                  bg="BG2", fg="FG2").pack(side="left", padx=(16, 4))

        self.brand_var = tk.StringVar(value="检测中...")
        self._reg(tk.Label(brand_bar, textvariable=self.brand_var,
                            font=("微软雅黑", 9, "bold"), width=8),
                  bg="BG2", fg="BLUE").pack(side="left")

        self._reg(tk.Label(brand_bar, text="型号:", font=("微软雅黑", 9)),
                  bg="BG2", fg="FG2").pack(side="left", padx=(20, 4))
        self.model_var = tk.StringVar(value="")
        self._reg(tk.Label(brand_bar, textvariable=self.model_var, font=("微软雅黑", 9)),
                  bg="BG2", fg="FG").pack(side="left")

        self._reg(tk.Label(brand_bar, text="序列号:", font=("微软雅黑", 9)),
                  bg="BG2", fg="FG2").pack(side="left", padx=(20, 4))
        self.serial_var = tk.StringVar(value="")
        self._reg(tk.Label(brand_bar, textvariable=self.serial_var, font=("微软雅黑", 9)),
                  bg="BG2", fg="FG").pack(side="left")

        self.tool_var = tk.StringVar(value="")
        self._reg(tk.Label(brand_bar, textvariable=self.tool_var,
                            font=("微软雅黑", 8), anchor="e"),
                  bg="BG2", fg="FG2").pack(side="right", padx=16)

        # ── 状态栏
        sbar = self._reg(tk.Frame(self.root, pady=6), bg="BG3")
        sbar.pack(fill="x")
        self.status_var = tk.StringVar(value="正在检测系统信息...")
        self._reg(tk.Label(sbar, textvariable=self.status_var, font=("微软雅黑", 9)),
                  bg="BG3", fg="FG2").pack(side="left", padx=16)
        self.spin_bar = ttk.Progressbar(sbar, mode="indeterminate", length=100)
        self.spin_bar.pack(side="right", padx=16)
        self.spin_bar.start(10)

        # ── 更新进度区（默认隐藏）
        self.upd_frame = self._reg(tk.Frame(self.root, pady=5, padx=18), bg="BG2")

        dl_row = self._reg(tk.Frame(self.upd_frame), bg="BG2")
        dl_row.pack(fill="x", pady=2)
        self._reg(tk.Label(dl_row, text="下载", width=4, font=("微软雅黑", 8, "bold")),
                  bg="BG2", fg="FG2").pack(side="left")
        self.dl_bar = ttk.Progressbar(dl_row, mode="determinate", length=1)
        self.dl_bar.pack(side="left", fill="x", expand=True, padx=(6, 8))
        self.dl_lbl_var = tk.StringVar(value="")
        self._reg(tk.Label(dl_row, textvariable=self.dl_lbl_var, width=14,
                            font=("微软雅黑", 8), anchor="w"),
                  bg="BG2", fg="FG2").pack(side="left")

        inst_row = self._reg(tk.Frame(self.upd_frame), bg="BG2")
        inst_row.pack(fill="x", pady=2)
        self._reg(tk.Label(inst_row, text="安装", width=4, font=("微软雅黑", 8, "bold")),
                  bg="BG2", fg="FG2").pack(side="left")
        self.inst_bar = ttk.Progressbar(inst_row, mode="determinate", length=1)
        self.inst_bar.pack(side="left", fill="x", expand=True, padx=(6, 8))
        self.inst_lbl_var = tk.StringVar(value="")
        self._reg(tk.Label(inst_row, textvariable=self.inst_lbl_var, width=14,
                            font=("微软雅黑", 8), anchor="w"),
                  bg="BG2", fg="FG2").pack(side="left")

        # ── 工具栏
        bar = ttk.Frame(self.root, padding=(12, 8))
        bar.pack(fill="x")
        self.btn_scan   = ttk.Button(bar, text="🔍  扫描驱动",     command=self.do_scan)
        self.btn_fix    = ttk.Button(bar, text="🔧  修复问题",     command=self.do_fix,    state="disabled")
        self.btn_update = ttk.Button(bar, text="⬆  检查更新",     command=self.do_update, state="disabled")
        self.btn_all    = ttk.Button(bar, text="✨  一键修复+更新", command=self.do_all,
                                     style="Accent.TButton",      state="disabled")
        self.btn_reboot = ttk.Button(bar, text="🔄  立即重启",     command=self.do_reboot, state="disabled")
        self.btn_dl_tool = ttk.Button(bar, text="⬇  下载品牌工具",
                                      command=self.do_download_tool, state="disabled")

        for btn in (self.btn_scan, self.btn_fix, self.btn_update):
            btn.pack(side="left", padx=4)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)
        self.btn_all.pack(side="left", padx=4)
        self.btn_dl_tool.pack(side="left", padx=4)
        self.btn_reboot.pack(side="right", padx=4)

        # 摘要行
        self.summary_var = tk.StringVar()
        self._reg(tk.Label(self.root, textvariable=self.summary_var,
                            font=("微软雅黑", 9), anchor="w", padx=18),
                  bg="BG", fg="FG2").pack(fill="x")

        ttk.Separator(self.root).pack(fill="x")

        # ── 主分割区
        pane = ttk.PanedWindow(self.root, orient="vertical")
        pane.pack(fill="both", expand=True, padx=10, pady=8)

        # 设备列表
        tf = ttk.Frame(pane)
        pane.add(tf, weight=3)
        cols = ("device", "error", "version", "action")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("device",  text="设备名称")
        self.tree.heading("error",   text="问题描述")
        self.tree.heading("version", text="驱动版本")
        self.tree.heading("action",  text="建议操作")
        self.tree.column("device",  width=310, minwidth=160, anchor="center")
        self.tree.column("error",   width=200, minwidth=120, anchor="center")
        self.tree.column("version", width=130, minwidth=80,  anchor="center")
        self.tree.column("action",  width=110, minwidth=80,  anchor="center")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)

        # 日志区
        lf = ttk.Frame(pane)
        pane.add(lf, weight=1)
        lh = ttk.Frame(lf)
        lh.pack(fill="x")
        ttk.Label(lh, text="操作日志", style="Sub.TLabel").pack(side="left", padx=6, pady=2)
        ttk.Button(lh, text="清空", command=self._clear_log).pack(side="right", padx=4, pady=2)
        self.log_box = self._reg(
            scrolledtext.ScrolledText(lf, font=("Consolas", 8), relief="flat", wrap="word"),
            bg="BG2", fg="FG2", ibg="GREEN",
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    # ── 系统检测线程 ──────────────────────────────────────────────────────────

    def _detect_system_thread(self):
        info = detect_system_info()
        self.sys_info = info
        brand = info["brand"]

        # 查找品牌工具（有 CLI 的品牌）
        tool_info = ""
        need_tool = False
        if brand == "Dell":
            self.dcu_path = find_dell_dcu()
            if self.dcu_path:
                tool_info = "更新工具: Dell Command Update ✓"
            else:
                tool_info = "未找到 Dell Command Update（使用 Windows Update）"
                need_tool = True
        elif brand == "Lenovo":
            self.lsu_path = find_lenovo_lsu()
            if self.lsu_path:
                tool_info = "更新工具: Lenovo System Update ✓"
            else:
                tool_info = "未找到 Lenovo System Update（使用 Windows Update）"
                need_tool = True
        elif brand == "Huanan":
            tool_info = "华南/杂牌主板 — 无官方工具，使用 Windows Update"
        elif brand in BRAND_TOOL_INFO and BRAND_TOOL_INFO[brand][0]:
            tool_name, _ = BRAND_TOOL_INFO[brand]
            tool_info = f"推荐工具: {tool_name}（点击「下载品牌工具」）"
            need_tool = True
        else:
            tool_info = "更新工具: Windows Update"

        # GPU 信息附加到 tool_info
        gpu_vendor = info.get("gpu_vendor", "")
        gpu_name   = info.get("gpu_name", "")
        if gpu_name and gpu_name != "未知":
            tool_info += f"  |  GPU: {gpu_name}"

        def _ui():
            brand_display = brand if brand != "Other" else info.get("raw_mfr", "未知品牌") or "未知品牌"
            self.brand_var.set(brand_display)
            self.model_var.set(info["model"])
            self.serial_var.set(info["serial"])
            self.tool_var.set(tool_info)
            self.spin_bar.stop()
            self.status_var.set("系统信息检测完成，点击「扫描驱动」开始")

            self.btn_dl_tool.configure(state="normal" if need_tool else "disabled")
            self.btn_scan.configure(state="normal")

            # 品牌标签高亮色
            brand_color = BRAND_COLORS.get(brand, self.T["BLUE"])
            for w, keys in self._tk_widgets:
                if keys.get("fg") == "BLUE":
                    try:
                        w.configure(fg=brand_color)
                    except Exception:
                        pass

        self.root.after(0, _ui)
        # 检测完成后自动扫描
        self.root.after(200, self.do_scan)

    # ── 进度条 ────────────────────────────────────────────────────────────────

    def _show_upd_progress(self, show):
        def _u():
            if show:
                self.upd_frame.pack(fill="x", before=self._toolbar_ref)
                self.dl_bar["value"] = self.inst_bar["value"] = 0
                self.dl_lbl_var.set("")
                self.inst_lbl_var.set("")
            else:
                self.upd_frame.pack_forget()
        self.root.after(0, _u)

    def _on_progress(self, phase, current, total, title=""):
        def _u():
            if phase == "download":
                if total > 0:
                    self.dl_bar["maximum"] = total
                    self.dl_bar["value"]   = current
                    pct = int(current / total * 100)
                    self.dl_lbl_var.set(f"{current}/{total}  {pct}%")
            elif phase == "install":
                if total > 0:
                    self.inst_bar["maximum"] = total
                    self.inst_bar["value"]   = current
                    pct = int(current / total * 100)
                    self.inst_lbl_var.set(f"{current}/{total}  {pct}%")
            elif phase == "done":
                self.dl_lbl_var.set("完成 ✓")
                self.inst_lbl_var.set("完成 ✓")
        self.root.after(0, _u)

    # ── 日志 ──────────────────────────────────────────────────────────────────

    def log(self, text):
        def _w():
            self.log_box.configure(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}] {text}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, _w)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── 状态 / 按钮 ───────────────────────────────────────────────────────────

    def _set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def _set_summary(self, text):
        self.root.after(0, lambda: self.summary_var.set(text))

    def _set_busy(self, busy, has_devices=False):
        def _u():
            sd = "disabled" if busy else "normal"
            sa = "disabled" if (busy or not has_devices) else "normal"
            self.btn_scan.configure(state=sd)
            self.btn_fix.configure(state=sa)
            self.btn_update.configure(state=sd)
            self.btn_all.configure(state=sa)
            if busy:
                self.spin_bar.start(10)
            else:
                self.spin_bar.stop()
        self.root.after(0, _u)

    def _refresh_tree(self):
        def _u():
            for row in self.tree.get_children():
                self.tree.delete(row)
            for d in self.devices:
                tag = "err" if d["action"] in ("reinstall", "install") else "warn"
                self.tree.insert("", "end", values=(
                    d["name"], d["errorDesc"], d["driverVersion"],
                    ACTION_LABELS.get(d["action"], d["action"]),
                ), tags=(tag,))
        self.root.after(0, _u)

    # ── 下载品牌工具 ──────────────────────────────────────────────────────────

    def do_download_tool(self):
        brand = self.sys_info.get("brand", "Other")
        tool_entry = BRAND_TOOL_INFO.get(brand)
        if not tool_entry or not tool_entry[1]:
            if brand == "Huanan":
                messagebox.showinfo(
                    "华南/杂牌主板说明",
                    "华南、精粤、昂达等杂牌主板没有官方驱动工具。\n\n"
                    "建议：\n"
                    "① 通过 Windows Update 自动安装驱动\n"
                    "② 前往设备管理器手动查找问题设备\n"
                    "③ 在主板型号+芯片组厂商官网下载对应驱动\n"
                    "   · 芯片组：Intel ARK / AMD 官网\n"
                    "   · 网卡：Realtek / Intel 官网\n"
                    "   · 声卡：Realtek 官网"
                )
            else:
                messagebox.showinfo("提示", "当前品牌暂无官方驱动工具信息。")
            return
        name, url = tool_entry
        hint = ""
        if brand in ("Dell", "Lenovo"):
            hint = f"\n\n安装完成后请重新启动本工具，将自动使用 {name} 进行精准驱动更新。"
        if messagebox.askyesno("下载品牌驱动工具",
                f"将打开浏览器前往【{name}】官方下载页面。{hint}\n\n是否继续？"):
            import webbrowser
            webbrowser.open(url)

    # ── 扫描 ──────────────────────────────────────────────────────────────────

    def do_scan(self):
        if self.running:
            return
        self.running = True
        self._set_busy(True)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        self.log("═" * 55)
        self.log("开始扫描设备驱动状态...")
        self._set_status("正在扫描...")
        self.devices = scan_devices()
        self._refresh_tree()
        n = len(self.devices)
        if n == 0:
            self._set_status("✓ 所有驱动状态正常")
            self._set_summary("扫描完成：未发现驱动问题 ✓")
            self.log("✓ 扫描完成，未发现任何驱动问题")
        else:
            fixable = sum(1 for d in self.devices
                          if d["action"] in ("reinstall", "install", "enable"))
            need_reboot = any(d["action"] == "reboot" for d in self.devices)
            self._set_summary(
                f"扫描完成：发现 {n} 个问题设备，其中 {fixable} 个可尝试自动修复"
                + ("，有设备需要重启" if need_reboot else ""))
            self.log(f"发现 {n} 个问题设备：")
            for d in self.devices:
                self.log(f"  • [{d['errorDesc']}]  {d['name']}")
            self._set_status(f"发现 {n} 个驱动问题")
            # 扫描发现需要重启的设备，直接启用重启按钮
            if need_reboot:
                self.reboot_flag = True
                self.root.after(0, lambda: self.btn_reboot.configure(state="normal"))
                self.log("  ⚠ 检测到需要重启才能生效的设备，建议立即重启计算机")
        self.running = False
        self._set_busy(False, has_devices=(n > 0))

    # ── 修复 ──────────────────────────────────────────────────────────────────

    def do_fix(self):
        if self.running:
            return
        if not is_admin():
            messagebox.showwarning("权限不足",
                "修复驱动需要管理员权限。\n请右键程序图标 → 以管理员身份运行。")
            return
        self.running = True
        self._set_busy(True)
        threading.Thread(target=self._fix_worker, daemon=True).start()

    def _fix_worker(self):
        self.log("═" * 55)
        self.log("开始修复问题驱动...")
        self._set_status("正在修复...")
        self._run_fix()
        self.running = False
        self._set_busy(False, has_devices=bool(self.devices))

    def _run_fix(self):
        targets = [d for d in self.devices
                   if d["action"] in ("reinstall", "install", "enable", "update")]
        if not targets:
            self.log("没有可自动修复的设备")
            return
        ok = sum(1 for d in targets if fix_device(d, self.log))
        self.log(f"修复处理：{ok}/{len(targets)} 个成功")
        self.log("重新扫描确认结果...")
        self.devices = scan_devices()
        self._refresh_tree()
        n = len(self.devices)
        if n == 0:
            self._set_summary("修复完成：所有驱动状态正常 ✓")
            self._set_status("✓ 所有驱动问题已修复")
        else:
            self._set_summary(f"修复完成：仍有 {n} 个问题，建议使用品牌工具更新驱动")
            self._set_status(f"修复后仍有 {n} 个问题")

    # ── 更新（品牌优先）──────────────────────────────────────────────────────

    def do_update(self):
        if self.running:
            return
        if not is_admin():
            messagebox.showwarning("权限不足",
                "安装驱动更新需要管理员权限。\n请右键程序图标 → 以管理员身份运行。")
            return
        self.running = True
        self._set_busy(True)
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        self.log("═" * 55)
        brand = self.sys_info.get("brand", "Other")
        self.log(f"品牌：{brand} | 型号：{self.sys_info.get('model','未知')}")
        self._set_status("正在检查驱动更新...")
        self._run_update()
        self.running = False
        self._set_busy(False, has_devices=bool(self.devices))

    def _run_update(self):
        brand = self.sys_info.get("brand", "Other")

        # ── Dell ─────────────────────────────────────────────────────────────
        if brand == "Dell" and self.dcu_path:
            self.log(f"使用 Dell Command Update: {self.dcu_path}")
            count, titles = dell_scan_updates(self.dcu_path, self.log)
            if count == 0:
                self._set_status("没有可用的 Dell 驱动更新")
                return
            if count < 0:
                self._set_status("Dell 扫描失败，请查看日志")
                return
            if titles:
                for t in titles:
                    self.log(f"  • {t}")
            self._show_upd_progress(True)
            self._set_status(f"正在安装 {count} 个 Dell 驱动更新...")
            ok, need_reboot = dell_apply_updates(self.dcu_path, self.log, self._on_progress)
            self._show_upd_progress(False)
            if ok:
                self._set_status("✓ Dell 驱动更新完成")
                self._handle_reboot(need_reboot)
            else:
                self._set_status("Dell 驱动更新失败，请查看日志")

        # ── Lenovo ───────────────────────────────────────────────────────────
        elif brand == "Lenovo" and self.lsu_path:
            self.log(f"使用 Lenovo System Update: {self.lsu_path}")
            self._show_upd_progress(True)
            self._set_status("正在通过 Lenovo System Update 更新驱动...")
            ok, need_reboot = lenovo_apply_updates(self.lsu_path, self.log, self._on_progress)
            self._show_upd_progress(False)
            if ok:
                self._set_status("✓ Lenovo 驱动更新完成")
                self._handle_reboot(need_reboot)
            else:
                self._set_status("Lenovo 驱动更新失败，请查看日志")

        # ── 通用回退：Windows Update ──────────────────────────────────────
        else:
            if brand in ("Dell", "Lenovo"):
                self.log(f"  ⚠ 未找到 {brand} 专用工具，回退使用 Windows Update")
                self.log(f"    建议安装品牌工具以获得更精准的驱动匹配")
            elif brand == "Huanan":
                self.log("  华南/杂牌主板：无官方驱动工具，使用 Windows Update")
                self.log("  提示：芯片组/网卡/声卡驱动可前往 Intel/AMD/Realtek 官网下载")
            elif brand in BRAND_TOOL_INFO and BRAND_TOOL_INFO[brand][0]:
                tool_name, tool_url = BRAND_TOOL_INFO[brand]
                self.log(f"  {brand} 品牌检测到，使用 Windows Update 搜索通用驱动")
                self.log(f"  提示：可点击「下载品牌工具」安装【{tool_name}】获得更精准的驱动")
            else:
                self.log(f"  品牌：{brand}，使用 Windows Update 搜索驱动更新...")

            updates = search_driver_updates_wua(self.log)
            if not updates:
                self._set_status("没有可用的驱动更新")
                return
            self.log(f"  找到 {len(updates)} 个驱动更新：")
            for u in updates:
                size_str = f"  ({u['size']} MB)" if u.get("size") else ""
                self.log(f"  • {u['title']}{size_str}")
            self._show_upd_progress(True)
            self._set_status(f"正在安装 {len(updates)} 个驱动更新...")
            ok, need_reboot = install_driver_updates_wua(self.log, self._on_progress)
            self._show_upd_progress(False)
            if ok:
                self._set_status("✓ 驱动更新安装完成")
                self._handle_reboot(need_reboot)
            else:
                self._set_status("驱动更新失败，请查看日志")

    def _handle_reboot(self, need_reboot):
        if need_reboot:
            self.reboot_flag = True
            self.root.after(0, lambda: self.btn_reboot.configure(state="normal"))
            self.log("⚠ 需要重启计算机以完成驱动更新")
            self.root.after(0, lambda: messagebox.showinfo(
                "需要重启", "驱动已更新，需要重启计算机才能生效。\n点击「立即重启」按钮。"))

    # ── 一键修复+更新 ─────────────────────────────────────────────────────────

    def do_all(self):
        if self.running:
            return
        if not is_admin():
            messagebox.showwarning("权限不足",
                "此操作需要管理员权限。\n请右键程序图标 → 以管理员身份运行。")
            return
        self.running = True
        self._set_busy(True)
        threading.Thread(target=self._all_worker, daemon=True).start()

    def _all_worker(self):
        self.log("═" * 55)
        self.log("▶ 一键修复 + 品牌精准驱动更新")
        self.log("── 第一阶段：修复问题驱动 ──")
        self._set_status("第一阶段：修复问题驱动...")
        self._run_fix()
        self.log("── 第二阶段：品牌精准驱动更新 ──")
        self._set_status("第二阶段：检查品牌驱动更新...")
        self._run_update()
        self.log("▶ 一键处理完成")
        self.running = False
        self._set_busy(False, has_devices=bool(self.devices))

    # ── 重启 ──────────────────────────────────────────────────────────────────

    def do_reboot(self):
        if messagebox.askyesno("确认重启", "确定立即重启计算机吗？\n请先保存所有工作。"):
            subprocess.run(["shutdown", "/r", "/t", "15",
                            "/c", "驱动更新完成，计算机将在 15 秒后重启"],
                           check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            messagebox.showinfo("重启倒计时",
                "计算机将在 15 秒后重启。\n如需取消请在命令行运行：shutdown /a")

    # ── 工具栏引用（用于进度条 pack 定位）────────────────────────────────────

    @property
    def _toolbar_ref(self):
        """返回工具栏帧，供 upd_frame pack(before=...) 使用"""
        # 遍历 root 子控件找到工具栏
        for child in self.root.pack_slaves():
            if isinstance(child, ttk.Frame):
                for sub in child.winfo_children():
                    if sub == self.btn_scan:
                        return child
        return None


# ─── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    if not is_admin():
        ans = ctypes.windll.user32.MessageBoxW(
            0,
            "建议以管理员身份运行以使用完整的修复和更新功能。\n\n是否以管理员身份重新启动？\n（选择[否]仍可使用扫描功能）",
            "驱动检测与修复工具",
            0x00000024,
        )
        if ans == 6:
            elevate()
            return

    root = tk.Tk()
    try:
        icon_path = os.path.join(
            os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
            else os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
