from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .classfile import ClassFormatError, parse_class


class Java9MacosEawtBridgeError(ValueError):
    pass


BRIDGE_NAME = "java9_macos_eawt_v308_required_surface"
V308_SOURCE_AUTHORITY_SHA256 = (
    "854f26ff9f134b0317572e7ac1688e6f"
    "40a231d5a4c66f8db5d655b7f45ce7c6"
)

V308_AUTHORITY = {
    "source_authority_sha256": V308_SOURCE_AUTHORITY_SHA256,
    "classfile_major": 53,
    "project_classes": {
        "rs/A/n.class": (
            "517d459c041e884dd9d64f3ac4db48bd"
            "3a49368cabedd50595e5b04f7a055b0b"
        ),
        "rs/A/o.class": (
            "2922f6460c8da38ef7fa14847a4cc2dc"
            "b3220f00b8ded7f425a4460ed8655ec4"
        ),
    },
    "openjdk9_source_blobs": {
        "com/apple/eawt/Application.java": (
            "9bcafeae1b117068af5e3df1124056ae4f651ea6"
        ),
        "com/apple/eawt/FullScreenAdapter.java": (
            "79fcd34b92002a568718ed8fdffd5221b9b4e316"
        ),
        "com/apple/eawt/FullScreenListener.java": (
            "d3490efcde7be2f4329b504d75554cb4eb3f5645"
        ),
        "com/apple/eawt/FullScreenUtilities.java": (
            "38472121b8b1419702e15b08bb475df90bde8db1"
        ),
        "com/apple/eawt/event/FullScreenEvent.java": (
            "3ff90ac5e1d3f71e93f6484145ab7721517b40c9"
        ),
    },
    "required_external_descriptors": [
        "com/apple/eawt/Application.getApplication:"
        "()Lcom/apple/eawt/Application;",
        "com/apple/eawt/Application.requestForeground:(Z)V",
        "com/apple/eawt/Application.requestUserAttention:(Z)V",
        "com/apple/eawt/FullScreenAdapter.<init>:()V",
        "com/apple/eawt/FullScreenUtilities.addFullScreenListenerTo:"
        "(Ljava/awt/Window;Lcom/apple/eawt/FullScreenListener;)V",
        "com/apple/eawt/FullScreenUtilities.setWindowCanFullScreen:"
        "(Ljava/awt/Window;Z)V",
        "com/apple/eawt/event/FullScreenEvent",
    ],
}

_SOURCES = {
    "com/apple/eawt/Application.java": """package com.apple.eawt;

public class Application {
    public static Application getApplication() {
        return null;
    }

    public void requestForeground(final boolean allWindows) {
    }

    public void requestUserAttention(final boolean critical) {
    }
}
""",
    "com/apple/eawt/FullScreenAdapter.java": """package com.apple.eawt;

import com.apple.eawt.event.FullScreenEvent;

public abstract class FullScreenAdapter implements FullScreenListener {
    public void windowEnteringFullScreen(final FullScreenEvent event) {
    }

    public void windowEnteredFullScreen(final FullScreenEvent event) {
    }

    public void windowExitingFullScreen(final FullScreenEvent event) {
    }

    public void windowExitedFullScreen(final FullScreenEvent event) {
    }
}
""",
    "com/apple/eawt/FullScreenListener.java": """package com.apple.eawt;

import com.apple.eawt.event.FullScreenEvent;
import java.util.EventListener;

public interface FullScreenListener extends EventListener {
    void windowEnteringFullScreen(FullScreenEvent event);

    void windowEnteredFullScreen(FullScreenEvent event);

    void windowExitingFullScreen(FullScreenEvent event);

    void windowExitedFullScreen(FullScreenEvent event);
}
""",
    "com/apple/eawt/FullScreenUtilities.java": """package com.apple.eawt;

import java.awt.Window;

public final class FullScreenUtilities {
    private FullScreenUtilities() {
    }

    public static void setWindowCanFullScreen(
        final Window window,
        final boolean canFullScreen
    ) {
    }

    public static void addFullScreenListenerTo(
        final Window window,
        final FullScreenListener listener
    ) {
    }

    public static void removeFullScreenListenerFrom(
        final Window window,
        final FullScreenListener listener
    ) {
    }
}
""",
    "com/apple/eawt/event/FullScreenEvent.java": """package com.apple.eawt.event;

import com.apple.eawt.Application;
import java.awt.Window;
import java.util.EventObject;

public class FullScreenEvent extends EventObject {
    public FullScreenEvent(final Window window) {
        super(Application.getApplication());
    }
}
""",
}

_EXPECTED_METHODS = {
    "com/apple/eawt/Application": {
        ("<init>", "()V"),
        ("getApplication", "()Lcom/apple/eawt/Application;"),
        ("requestForeground", "(Z)V"),
        ("requestUserAttention", "(Z)V"),
    },
    "com/apple/eawt/FullScreenAdapter": {
        ("<init>", "()V"),
        (
            "windowEnteringFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
        (
            "windowEnteredFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
        (
            "windowExitingFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
        (
            "windowExitedFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
    },
    "com/apple/eawt/FullScreenListener": {
        (
            "windowEnteringFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
        (
            "windowEnteredFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
        (
            "windowExitingFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
        (
            "windowExitedFullScreen",
            "(Lcom/apple/eawt/event/FullScreenEvent;)V",
        ),
    },
    "com/apple/eawt/FullScreenUtilities": {
        ("<init>", "()V"),
        (
            "setWindowCanFullScreen",
            "(Ljava/awt/Window;Z)V",
        ),
        (
            "addFullScreenListenerTo",
            "(Ljava/awt/Window;Lcom/apple/eawt/FullScreenListener;)V",
        ),
        (
            "removeFullScreenListenerFrom",
            "(Ljava/awt/Window;Lcom/apple/eawt/FullScreenListener;)V",
        ),
    },
    "com/apple/eawt/event/FullScreenEvent": {
        ("<init>", "(Ljava/awt/Window;)V"),
    },
}

_EXPECTED_SUPERS = {
    "com/apple/eawt/Application": "java/lang/Object",
    "com/apple/eawt/FullScreenAdapter": "java/lang/Object",
    "com/apple/eawt/FullScreenListener": "java/lang/Object",
    "com/apple/eawt/FullScreenUtilities": "java/lang/Object",
    "com/apple/eawt/event/FullScreenEvent": "java/util/EventObject",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _tree_digest(root: Path, suffix: str) -> tuple[str, int, int]:
    rows = []
    total_bytes = 0
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.name.endswith(suffix)
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in files:
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        rows.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
        total_bytes += len(data)
    return _stable_digest(rows), len(files), total_bytes


def _require_executable(command: str) -> str:
    resolved = shutil.which(command)
    if resolved is None:
        path = Path(command)
        if path.is_file():
            resolved = str(path.resolve())
    if resolved is None:
        raise Java9MacosEawtBridgeError(
            f"javac executable not found: {command!r}"
        )
    return resolved


def _write_sources(source_root: Path) -> list[Path]:
    written = []
    for rel, content in sorted(_SOURCES.items()):
        target = source_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        written.append(target)
    return written


def _verify_classes(classes_root: Path) -> None:
    actual = {
        path.relative_to(classes_root).as_posix()
        for path in classes_root.rglob("*.class")
    }
    expected = {
        name + ".class"
        for name in _EXPECTED_METHODS
    }
    if actual != expected:
        raise Java9MacosEawtBridgeError(
            "generated bridge class set drifted"
        )

    for internal, expected_methods in _EXPECTED_METHODS.items():
        path = classes_root / (internal + ".class")
        try:
            parsed = parse_class(path.read_bytes())
        except ClassFormatError as exc:
            raise Java9MacosEawtBridgeError(str(exc)) from exc

        if parsed.name != internal:
            raise Java9MacosEawtBridgeError(
                "generated bridge internal name drifted"
            )
        if parsed.major != 53:
            raise Java9MacosEawtBridgeError(
                "generated bridge is not Java 9 bytecode"
            )
        if parsed.super_name != _EXPECTED_SUPERS[internal]:
            raise Java9MacosEawtBridgeError(
                "generated bridge superclass drifted"
            )

        methods = {
            (str(method["name"]), str(method["descriptor"]))
            for method in parsed.methods
        }
        if methods != expected_methods:
            raise Java9MacosEawtBridgeError(
                "generated bridge method surface drifted"
            )

    adapter = parse_class(
        (
            classes_root
            / "com/apple/eawt/FullScreenAdapter.class"
        ).read_bytes()
    )
    if adapter.interfaces != ["com/apple/eawt/FullScreenListener"]:
        raise Java9MacosEawtBridgeError(
            "FullScreenAdapter listener authority drifted"
        )


def bridge_class_entries() -> frozenset[str]:
    return frozenset(
        internal + ".class"
        for internal in _EXPECTED_METHODS
    )


def bridge_id() -> str:
    material = {
        "name": BRIDGE_NAME,
        "authority": V308_AUTHORITY,
        "sources": _SOURCES,
        "expected_methods": {
            name: sorted([list(row) for row in methods])
            for name, methods in sorted(_EXPECTED_METHODS.items())
        },
    }
    return (
        "J9EAWTBRIDGE_"
        + _stable_digest(material)[:20].upper()
    )


def build_java9_macos_eawt_compile_bridge(
    out_dir: Path,
    *,
    javac_command: str = "javac",
    release: int | None = 9,
) -> tuple[Path, dict[str, Any]]:
    if release != 9:
        raise Java9MacosEawtBridgeError(
            "Java 9 macOS eAWT bridge requires target release 9"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise Java9MacosEawtBridgeError(
            "bridge output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    source_root = out_dir / "source"
    classes_root = out_dir / "classes"
    empty_sourcepath = out_dir / "empty-sourcepath"
    source_root.mkdir()
    classes_root.mkdir()
    empty_sourcepath.mkdir()

    sources = _write_sources(source_root)
    source_sha, source_count, source_bytes = _tree_digest(
        source_root,
        ".java",
    )
    if source_count != len(_SOURCES):
        raise Java9MacosEawtBridgeError(
            "bridge source count drifted"
        )

    javac = _require_executable(javac_command)
    proc = subprocess.run(
        [
            javac,
            "-proc:none",
            "-encoding",
            "UTF-8",
            "-Xlint:none",
            "-sourcepath",
            str(empty_sourcepath),
            "-d",
            str(classes_root),
            "--release",
            "9",
            *[str(path) for path in sources],
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise Java9MacosEawtBridgeError(
            "Java 9 macOS eAWT bridge javac failed:\n"
            + proc.stdout
            + proc.stderr
        )

    _verify_classes(classes_root)
    class_sha, class_count, class_bytes = _tree_digest(
        classes_root,
        ".class",
    )

    report = {
        "schema_version": 1,
        "kind": "compile_only_platform_bridge",
        "bridge_id": bridge_id(),
        "name": BRIDGE_NAME,
        "target_release": 9,
        "authority": V308_AUTHORITY,
        "source_tree_sha256": source_sha,
        "source_count": source_count,
        "source_total_bytes": source_bytes,
        "class_tree_sha256": class_sha,
        "class_count": class_count,
        "class_total_bytes": class_bytes,
        "runtime_allowed": False,
    }
    (
        out_dir / "java9-macos-eawt-bridge.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return classes_root, report
