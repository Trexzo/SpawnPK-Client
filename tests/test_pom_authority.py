from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.pom_authority import (
    PomAuthorityError,
    parse_root_pom_authority,
    verify_pom_transfer,
)


_POM = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>example</groupId>
  <artifactId>client</artifactId>
  <version>1.0</version>
  <properties>
    <lib.version>2.3</lib.version>
    <maven.compiler.source>20</maven.compiler.source>
  </properties>
  <repositories>
    <repository>
      <id>repo</id>
      <url>https://example.invalid/maven</url>
      <snapshots>
        <enabled>true</enabled>
      </snapshots>
    </repository>
  </repositories>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.demo</groupId>
        <artifactId>demo-bom</artifactId>
        <version>9</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.demo</groupId>
      <artifactId>lib</artifactId>
      <version>${lib.version}</version>
    </dependency>
    <dependency>
      <groupId>org.demo</groupId>
      <artifactId>native</artifactId>
      <classifier>natives-windows</classifier>
      <scope>runtime</scope>
    </dependency>
  </dependencies>
  <build>
    <outputDirectory>../bin</outputDirectory>
    <resources>
      <resource><directory>src/resources</directory></resource>
    </resources>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <source>9</source>
          <target>9</target>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""


class PomAuthorityTests(unittest.TestCase):
    def _jar(
        self,
        path: Path,
        *,
        include_pom: bool,
        dep_bytes: bytes = b"dep",
        service_newline: bool = True,
        project_bytes: bytes = b"project",
    ) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            if include_pom:
                archive.writestr("pom.xml", _POM)
                archive.writestr("build.xml", "project metadata")
            archive.writestr("rs/Client.class", project_bytes)
            archive.writestr("tools/Probe.class", b"tool")
            archive.writestr("org/demo/Lib.class", dep_bytes)
            service = b"org.demo.Provider"
            if service_newline:
                service += b"\n"
            archive.writestr(
                "META-INF/services/org.demo.Service",
                service,
            )
            archive.writestr(
                "META-INF/data.txt",
                b"same-resource",
            )

    def test_root_pom_preserves_raw_and_resolved_authority(self):
        with tempfile.TemporaryDirectory() as td:
            jar = Path(td) / "source.jar"
            self._jar(jar, include_pom=True)

            report = parse_root_pom_authority(jar)

            self.assertTrue(
                report["pom_authority_id"].startswith("POMAUTH_")
            )
            self.assertEqual(
                report["project"]["group_id"]["resolved"],
                "example",
            )
            self.assertEqual(
                report["dependencies"][0]["version"],
                {
                    "raw": "${lib.version}",
                    "resolved": "2.3",
                    "unresolved_properties": [],
                },
            )
            self.assertIsNone(
                report["dependencies"][1]["version"]["resolved"]
            )
            self.assertEqual(
                report["dependency_management"][0]["scope"]["resolved"],
                "import",
            )
            plugin = report["build"]["plugins"][0]
            config = {
                row["name"]: row["value"]["resolved"]
                for row in plugin["configuration"]
            }
            self.assertEqual(config, {"source": "9", "target": "9"})
            properties = {
                row["name"]: row["value"]
                for row in report["properties"]
            }
            self.assertEqual(
                properties["maven.compiler.source"],
                "20",
            )

    def test_missing_root_pom_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            jar = Path(td) / "target.jar"
            self._jar(jar, include_pom=False)

            with self.assertRaises(PomAuthorityError):
                parse_root_pom_authority(jar)

    def test_transfer_accepts_exact_dependency_classes_and_service_newline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.jar"
            target = root / "target.jar"
            self._jar(
                source,
                include_pom=True,
                service_newline=False,
                project_bytes=b"source-project",
            )
            self._jar(
                target,
                include_pom=False,
                service_newline=True,
                project_bytes=b"target-project",
            )

            report = verify_pom_transfer(source, target)

            self.assertTrue(report["transfer_accepted"])
            self.assertFalse(report["target_contains_pom_entry"])
            classes = report["dependency_class_surface"]
            self.assertEqual(classes["source_count"], 1)
            self.assertEqual(classes["target_count"], 1)
            self.assertEqual(
                classes["byte_identical_common_count"],
                1,
            )
            payload = report["non_project_payload_surface"]
            self.assertEqual(
                payload[
                    "normalized_text_equivalent_differences"
                ],
                ["META-INF/services/org.demo.Service"],
            )
            self.assertEqual(
                payload["non_equivalent_differences"],
                [],
            )

    def test_transfer_rejects_different_dependency_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.jar"
            target = root / "target.jar"
            self._jar(
                source,
                include_pom=True,
                dep_bytes=b"one",
            )
            self._jar(
                target,
                include_pom=False,
                dep_bytes=b"two",
            )

            report = verify_pom_transfer(source, target)

            self.assertFalse(report["transfer_accepted"])
            self.assertEqual(
                report["dependency_class_surface"][
                    "different_common"
                ],
                ["org/demo/Lib.class"],
            )


if __name__ == "__main__":
    unittest.main()
