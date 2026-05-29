SIRIS - Pruebas automatizadas v0.1 Backend/API

1. Copiar el contenido de este ZIP sobre la raíz del proyecto:
   D:\SIRIS

2. Verificar que queden estos archivos:
   D:\SIRIS\backend\tests\conftest.py
   D:\SIRIS\backend\tests\test_auth_api.py
   D:\SIRIS\backend\tests\test_study_area_and_security_api.py
   D:\SIRIS\backend\pytest.ini
   D:\SIRIS\scripts_tests\run_backend_api_tests.ps1

3. Ejecutar:
   cd D:\SIRIS
   powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_backend_api_tests.ps1

4. Evidencia:
   D:\SIRIS\tests_evidence\backend_api\backend_api_tests_<fecha>.log

5. Captura recomendada:
   Tomar una captura de pantalla de la terminal cuando aparezca "Resultado: APROBADO."
   y guardar la captura en:
   D:\SIRIS\tests_evidence\backend_api\
