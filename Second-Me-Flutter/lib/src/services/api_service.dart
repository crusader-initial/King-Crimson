import 'dart:io';
import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';

class ApiService {
  late final Dio _dio;

  ApiService() {
    // Android Emulator uses 10.0.2.2, iOS Simulator uses localhost
    final baseUrl = Platform.isAndroid 
        ? 'http://10.0.2.2:8000/api' 
        : 'http://localhost:8000/api';

    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));
  }

  Future<Map<String, dynamic>> uploadDocument(PlatformFile file) async {
    try {
      String fileName = file.name;
      String? filePath = file.path;

      if (filePath == null) {
        throw Exception('File path is null');
      }

      FormData formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(filePath, filename: fileName),
      });

      final response = await _dio.post(
        '/file',
        data: formData,
        options: Options(
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        ),
      );

      return response.data;
    } catch (e) {
      throw Exception('Failed to upload document: $e');
    }
  }

  Future<Map<String, dynamic>> sendChatMessage(String query) async {
    try {
      final response = await _dio.post(
        '/chat',
        data: {'query': query},
      );

      return response.data;
    } catch (e) {
      throw Exception('Failed to send message: $e');
    }
  }
}
