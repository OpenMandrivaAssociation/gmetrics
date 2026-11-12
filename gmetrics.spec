Name:		gmetrics
Version:	2.1.0
Release:	1
Summary:	Size and complexity metrics for Groovy source
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/dx42/gmetrics
# Tag v2.1.0, built as the Groovy 4 artifact GMetrics-Groovy4.
# The Gradle wrapper jar is not in this archive. Sources are compiled
# with Groovy's FileSystemCompiler. The Gradle tool is not invoked.
Source0:	gmetrics-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	apache-groovy
BuildRequires:	antlr4
BuildRequires:	objectweb-asm
BuildRequires:	picocli
BuildRequires:	jansi
BuildRequires:	ant
BuildRequires:	mvn(org.slf4j:slf4j-api)
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
# The Ant task classes import org.apache.tools.ant. Cooker ant has no mvn() provide.
Requires:	ant

%description
org.gmetrics:GMetrics-Groovy4 2.1.0. CodeNarc 3.7.0 for Groovy 4
depends on this artifact. The Groovy sources are compiled with
FileSystemCompiler from apache-groovy 4.0.33. MethodCountMetric
counts the methods in a class.

%prep
%autosetup -n gmetrics-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
find src/main -name '*.groovy' | sort > groovy.list
test "$(wc -l < groovy.list)" -eq 100
grep -qx '%{version}' src/main/resources/gmetrics-version.txt

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
CP=%{_javadir}/apache-groovy.jar
for extra in \
	%{_javadir}/apache-groovy-xml.jar \
	%{_javadir}/apache-groovy-ant.jar \
	%{_javadir}/apache-groovy-templates.jar \
	%{_javadir}/slf4j-api.jar \
	%{_javadir}/ant.jar \
	%{_javadir}/antlr4-runtime.jar \
	%{_javadir}/asm.jar \
	%{_javadir}/asm-commons.jar \
	%{_javadir}/asm-tree.jar \
	%{_javadir}/asm-util.jar \
	%{_javadir}/picocli.jar \
	/usr/lib/java/jansi/jansi.jar
do
	test -s "$extra"
	CP="$CP:$extra"
done
mkdir -p classes
java -Dgroovy.target.bytecode=11 -cp "$CP" org.codehaus.groovy.tools.FileSystemCompiler \
	--classpath "$CP" -d classes @groovy.list
test "$(find classes -name '*.class' | wc -l)" -eq 268
for cls in \
	org.gmetrics.metric.methodcount.MethodCountMetric \
	org.gmetrics.source.SourceString \
	org.gmetrics.GMetricsRunner
do
	javap -v -classpath classes "$cls" | grep -F -q 'major version: 55'
done
cp -a src/main/resources/. classes/
test -s classes/gmetrics-version.txt
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: org.gmetrics' > manifest.mf
jar cfm gmetrics.jar manifest.mf -C classes .
jar i gmetrics.jar
jar tf gmetrics.jar | grep -qx 'gmetrics-version.txt'
jar tf gmetrics.jar | grep -F -q 'org/gmetrics/metric/methodcount/MethodCountMetric.class'
desc=$(jar --describe-module --file gmetrics.jar)
printf '%s\n' "$desc" | grep -F -q 'org.gmetrics'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	printf '%s\n' "$desc"
	exit 1
fi

cat > gmetrics.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.gmetrics</groupId>
  <artifactId>GMetrics-Groovy4</artifactId>
  <version>%{version}</version>
  <name>GMetrics-Groovy4</name>
  <description>Size and complexity metrics for Groovy source code.</description>
  <url>https://github.com/dx42/gmetrics</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.apache.groovy</groupId>
      <artifactId>groovy</artifactId>
      <version>4.0.33</version>
    </dependency>
    <dependency>
      <groupId>org.apache.groovy</groupId>
      <artifactId>groovy-xml</artifactId>
      <version>4.0.33</version>
    </dependency>
    <dependency>
      <groupId>org.apache.groovy</groupId>
      <artifactId>groovy-ant</artifactId>
      <version>4.0.33</version>
    </dependency>
    <dependency>
      <groupId>org.apache.groovy</groupId>
      <artifactId>groovy-templates</artifactId>
      <version>4.0.33</version>
    </dependency>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.17</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact gmetrics.pom:gmetrics.jar \
	--file-name gmetrics \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/org.gmetrics/GMetrics-Groovy4.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "GMetrics-Groovy4"' "$idx"
test -s %{buildroot}%{_javadir}/gmetrics.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
JAR=%{buildroot}%{_javadir}/gmetrics.jar
test -s "$JAR"
CP=%{_javadir}/apache-groovy.jar
for extra in \
	%{_javadir}/apache-groovy-xml.jar \
	%{_javadir}/apache-groovy-ant.jar \
	%{_javadir}/apache-groovy-templates.jar \
	%{_javadir}/slf4j-api.jar \
	%{_javadir}/ant.jar \
	%{_javadir}/antlr4-runtime.jar \
	%{_javadir}/asm.jar \
	%{_javadir}/asm-commons.jar \
	%{_javadir}/asm-tree.jar \
	%{_javadir}/asm-util.jar \
	%{_javadir}/picocli.jar \
	/usr/lib/java/jansi/jansi.jar
do
	test -s "$extra"
	CP="$CP:$extra"
done
mkdir -p check
cat > check/Smoke.groovy << 'EOF'
import org.gmetrics.metric.methodcount.MethodCountMetric
import org.gmetrics.source.SourceString

def text = '''
class MyClass {
    void a() { return 1 }
    void b() { return 2 }
}
'''
def source = new SourceString(text)
def metric = new MethodCountMetric()
def result = metric.applyToClass(source.ast.classes[0], source)
def count = result.classMetricResult.number
if (count != 2) {
    throw new AssertionError(String.valueOf(count))
}
println "gmetrics_ok MethodCount ${count}"
EOF
java -Dgroovy.target.bytecode=11 -cp "$CP" org.codehaus.groovy.tools.FileSystemCompiler \
	--classpath "$JAR:$CP" -d check check/Smoke.groovy
"$JAVA_HOME/bin/java" -cp "check:$JAR:$CP" Smoke > check/out.txt
cat check/out.txt
grep -F -qx 'gmetrics_ok MethodCount 2' check/out.txt

%files -f .mfiles
%doc README.md CHANGELOG.md NOTICE.txt
%license LICENSE.txt
