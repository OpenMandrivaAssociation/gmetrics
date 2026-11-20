Name:		gmetrics
Version:	3.0.0
Release:	1
Summary:	Size and complexity metrics for Groovy source
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/dx42/gmetrics
# Tag v3.0.0. The Gradle wrapper jar is removed before lookaside.
# Sources are compiled with Groovy's FileSystemCompiler.
Source0:	https://github.com/dx42/gmetrics/archive/refs/tags/v%{version}.tar.gz#/gmetrics-%{version}.tar.gz
# Tag v2.1.0, the Groovy 4 artifact CodeNarc 3.7.0 still requires.
Source1:	gmetrics-2.1.0.tar.gz

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
org.gmetrics:GMetrics %{version}. This release drops Groovy 3 and
renames the artifact from GMetrics-Groovy4. CodeNarc 3.7.0 still
needs org.gmetrics:GMetrics-Groovy4 2.1.0, so that jar stays as
gmetrics.jar. %{version} is GMetrics.jar. Both jars contain
org.gmetrics and must not share a classpath. GroovyVersion reports
whether the runtime is Groovy 4 or Groovy 5.

%prep
%autosetup -n gmetrics-%{version} -p1
mkdir -p side
tar -xf %{SOURCE1} -C side
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
find src/main -name '*.groovy' | sort > groovy300.list
find side/gmetrics-2.1.0/src/main -name '*.groovy' | sort > groovy210.list
test "$(wc -l < groovy300.list)" -eq 101
test "$(wc -l < groovy210.list)" -eq 100
grep -qx '%{version}' src/main/resources/gmetrics-version.txt
grep -qx '2.1.0' side/gmetrics-2.1.0/src/main/resources/gmetrics-version.txt

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

compile_tree() {
	list=$1
	out=$2
	expect=$3
	mkdir -p "$out"
	java -Dgroovy.target.bytecode=11 -cp "$CP" org.codehaus.groovy.tools.FileSystemCompiler \
		--classpath "$CP" -d "$out" @"$list"
	test "$(find "$out" -name '*.class' | wc -l)" -eq "$expect"
}
compile_tree groovy300.list classes300 269
compile_tree groovy210.list classes210 268
cp -a src/main/resources/. classes300/
cp -a side/gmetrics-2.1.0/src/main/resources/. classes210/
test "$(cat classes300/gmetrics-version.txt)" = "%{version}"
test "$(cat classes210/gmetrics-version.txt)" = "2.1.0"
for cls in \
	org.gmetrics.metric.methodcount.MethodCountMetric \
	org.gmetrics.source.SourceString \
	org.gmetrics.GMetricsRunner \
	org.gmetrics.util.GroovyVersion
do
	javap -v -classpath classes300 "$cls" | grep -F -q 'major version: 55'
done
javap -v -classpath classes210 org.gmetrics.metric.methodcount.MethodCountMetric | grep -F -q 'major version: 55'
if javap -classpath classes210 org.gmetrics.util.GroovyVersion >/dev/null 2>&1; then
	echo "GroovyVersion must stay out of the 2.1.0 jar" >&2
	exit 1
fi

jar_one() {
	classes=$1
	dest=$2
	printf 'Manifest-Version: 1.0\nAutomatic-Module-Name: org.gmetrics\n\n' > "$dest.mf"
	jar cfm "$dest" "$dest.mf" -C "$classes" .
	jar i "$dest"
	jar tf "$dest" | grep -qx 'gmetrics-version.txt'
	jar tf "$dest" | grep -F -q 'org/gmetrics/metric/methodcount/MethodCountMetric.class'
	desc=$(jar --describe-module --file "$dest")
	printf '%s\n' "$desc" | grep -F -q 'org.gmetrics'
	if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
		printf '%s\n' "$desc"
		exit 1
	fi
}
jar_one classes300 GMetrics.jar
jar_one classes210 gmetrics.jar
mkdir -p ver300 ver210
( cd ver300 && jar xf ../GMetrics.jar gmetrics-version.txt )
( cd ver210 && jar xf ../gmetrics.jar gmetrics-version.txt )
test "$(cat ver300/gmetrics-version.txt)" = "%{version}"
test "$(cat ver210/gmetrics-version.txt)" = "2.1.0"
jar tf GMetrics.jar | grep -F -q 'org/gmetrics/util/GroovyVersion.class'
if jar tf gmetrics.jar | grep -F -q 'org/gmetrics/util/GroovyVersion.class'; then
	echo "GroovyVersion leaked into gmetrics.jar" >&2
	exit 1
fi

cat > GMetrics.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.gmetrics</groupId>
  <artifactId>GMetrics</artifactId>
  <version>%{version}</version>
  <name>GMetrics</name>
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
cat > gmetrics.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.gmetrics</groupId>
  <artifactId>GMetrics-Groovy4</artifactId>
  <version>2.1.0</version>
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
: > .mfiles
install_one() {
	pom=$1
	jar=$2
	name=$3
	sysjar install --buildroot %{buildroot} \
		--artifact "${pom}:${jar}" \
		--file-name "$name" \
		--filelist ".mfiles-${name}"
	while IFS= read -r line; do
		grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
	done < ".mfiles-${name}"
}
install_one gmetrics.pom gmetrics.jar gmetrics
install_one GMetrics.pom GMetrics.jar GMetrics
idx210="%{buildroot}/usr/share/sysjar/index/org.gmetrics/GMetrics-Groovy4.sysjar"
idx300="%{buildroot}/usr/share/sysjar/index/org.gmetrics/GMetrics.sysjar"
test -s "$idx210"
test -s "$idx300"
grep -F -q '"version": "2.1.0"' "$idx210"
grep -F -q '"artifactId": "GMetrics-Groovy4"' "$idx210"
grep -F -q '"version": "%{version}"' "$idx300"
grep -F -q '"artifactId": "GMetrics"' "$idx300"
test -s %{buildroot}%{_javadir}/gmetrics.jar
test -s %{buildroot}%{_javadir}/GMetrics.jar
mkdir -p installed210 installed300
( cd installed210 && jar xf %{buildroot}%{_javadir}/gmetrics.jar gmetrics-version.txt )
( cd installed300 && jar xf %{buildroot}%{_javadir}/GMetrics.jar gmetrics-version.txt )
test "$(cat installed210/gmetrics-version.txt)" = "2.1.0"
test "$(cat installed300/gmetrics-version.txt)" = "%{version}"

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
OLD=%{buildroot}%{_javadir}/gmetrics.jar
NEW=%{buildroot}%{_javadir}/GMetrics.jar
test -s "$OLD"
test -s "$NEW"
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
mkdir -p check/old check/new
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
/bin/cp check/Smoke.groovy check/old/Smoke210.groovy
/bin/cp check/Smoke.groovy check/new/Smoke300.groovy
sed -i 's/gmetrics_ok/gmetrics210_ok/' check/old/Smoke210.groovy
sed -i 's/gmetrics_ok/gmetrics300_ok/' check/new/Smoke300.groovy
java -Dgroovy.target.bytecode=11 -cp "$CP" org.codehaus.groovy.tools.FileSystemCompiler \
	--classpath "$OLD:$CP" -d check/old check/old/Smoke210.groovy
java -Dgroovy.target.bytecode=11 -cp "$CP" org.codehaus.groovy.tools.FileSystemCompiler \
	--classpath "$NEW:$CP" -d check/new check/new/Smoke300.groovy
"$JAVA_HOME/bin/java" -cp "check/old:$OLD:$CP" Smoke210 > check/old.txt
"$JAVA_HOME/bin/java" -cp "check/new:$NEW:$CP" Smoke300 > check/new.txt
cat check/old.txt check/new.txt
grep -F -qx 'gmetrics210_ok MethodCount 2' check/old.txt
grep -F -qx 'gmetrics300_ok MethodCount 2' check/new.txt

%files -f .mfiles
%doc README.md CHANGELOG.md NOTICE.txt
%license LICENSE.txt
