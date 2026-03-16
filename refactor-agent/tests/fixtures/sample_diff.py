"""Sample git diff fixtures for use across test suites.

These are plain strings — no filesystem access, no subprocess calls.
"""

SAMPLE_UNIFIED_DIFF = """\
diff --git a/app/service.py b/app/service.py
index 1234567..abcdefg 100644
--- a/app/service.py
+++ b/app/service.py
@@ -1,5 +1,10 @@
 class MyService:
-    def do_thing(self):
-        pass
+    def do_thing(self) -> None:
+        \"\"\"Perform the main operation.\"\"\"
+        # TODO: implement
+        raise NotImplementedError
"""

EMPTY_DIFF = ""

MULTI_FILE_DIFF = """\
diff --git a/app/models.py b/app/models.py
new file mode 100644
--- /dev/null
+++ b/app/models.py
@@ -0,0 +1,5 @@
+from dataclasses import dataclass
+
+@dataclass
+class User:
+    id: int
diff --git a/app/service.py b/app/service.py
--- a/app/service.py
+++ b/app/service.py
@@ -3,3 +3,4 @@
 class MyService:
-    pass
+    def run(self) -> None:
+        raise NotImplementedError
"""

DELETED_FILE_DIFF = """\
diff --git a/app/legacy.py b/app/legacy.py
deleted file mode 100644
index 2e65efe..0000000
--- a/app/legacy.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def legacy() -> None:
-    print("legacy")
-
"""

RENAMED_FILE_DIFF = """\
diff --git a/app/old_name.py b/app/new_name.py
similarity index 100%
rename from app/old_name.py
rename to app/new_name.py
"""

GENERATED_FILE_DIFF = """\
diff --git a/dist/bundle.min.js b/dist/bundle.min.js
new file mode 100644
--- /dev/null
+++ b/dist/bundle.min.js
@@ -0,0 +1,2 @@
+console.log("generated");
+//# sourceMappingURL=bundle.min.js.map
"""

CSHARP_DIFF = """\
diff --git a/src/App/Program.cs b/src/App/Program.cs
index 1234567..abcdef0 100644
--- a/src/App/Program.cs
+++ b/src/App/Program.cs
@@ -1,3 +1,4 @@
 using System;
+using Microsoft.Extensions.Hosting;
 
 Console.WriteLine("Hello World");
"""

ANGULAR_TYPESCRIPT_DIFF = """\
diff --git a/src/app/app.component.ts b/src/app/app.component.ts
index 1111111..2222222 100644
--- a/src/app/app.component.ts
+++ b/src/app/app.component.ts
@@ -1,3 +1,5 @@
 import { Component } from '@angular/core';
+import { RouterOutlet } from '@angular/router';
 
 @Component({
+  imports: [RouterOutlet],
 })
"""

ANGULAR_TEMPLATE_DIFF = """\
diff --git a/src/app/app.component.html b/src/app/app.component.html
index 3333333..4444444 100644
--- a/src/app/app.component.html
+++ b/src/app/app.component.html
@@ -1,2 +1,3 @@
 <section>
+  <router-outlet></router-outlet>
 </section>
"""

ANGULAR_STYLES_DIFF = """\
diff --git a/src/app/app.component.scss b/src/app/app.component.scss
index 5555555..6666666 100644
--- a/src/app/app.component.scss
+++ b/src/app/app.component.scss
@@ -1,2 +1,5 @@
 :host {
	 display: block;
+  padding: 1rem;
+
+  background: #fff;
 }
"""

ANGULAR_CONFIG_DIFF = """\
diff --git a/angular.json b/angular.json
index 7777777..8888888 100644
--- a/angular.json
+++ b/angular.json
@@ -1,3 +1,4 @@
 {
+  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
   "version": 1
 }
"""

CSHARP_PROJECT_DIFF = """\
diff --git a/src/App/App.csproj b/src/App/App.csproj
index 9999999..aaaaaaa 100644
--- a/src/App/App.csproj
+++ b/src/App/App.csproj
@@ -1,3 +1,4 @@
 <Project Sdk="Microsoft.NET.Sdk.Web">
+  <PropertyGroup><Nullable>enable</Nullable></PropertyGroup>
 </Project>
"""
