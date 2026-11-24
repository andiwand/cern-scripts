#include <onnxruntime_cxx_api.h>
#include <fstream>
#include <string>
OrtStatus* ORT_API_CALL capture(void*, const char* name, const OrtValue* value,
 const OrtExternalInitializerInfo*, OrtExternalInitializerInfo** loc) {
 *loc=nullptr;
 try {
   std::string key(name);
   if(key.ends_with(".weight") || key.ends_with(".bias")) {
     Ort::ExternalInitializerInfo info("native-weights",0,Ort::ConstValue(value).GetTensorSizeInBytes());
     *loc=info.release();
   }
   return nullptr;
 }catch(const std::exception& e){return Ort::GetApi().CreateStatus(ORT_FAIL,e.what());}
}
OrtStatus* ORT_API_CALL write(void* s,const void* data,size_t n){
 static_cast<std::ofstream*>(s)->write(static_cast<const char*>(data),n);return nullptr;
}
int main(int argc,char** argv){
 if(argc!=3)return 2;
 Ort::Env env(ORT_LOGGING_LEVEL_WARNING,"probe");
 Ort::SessionOptions session;session.SetIntraOpNumThreads(1).SetInterOpNumThreads(1);
 session.SetGraphOptimizationLevel(ORT_DISABLE_ALL);
 Ort::ModelCompilationOptions options(env,session);
 options.SetGraphOptimizationLevel(ORT_DISABLE_ALL);options.SetInputModelPath(argv[1]);
 std::ofstream out(argv[2],std::ios::binary);
 options.SetOutputModelWriteFunc(write,&out);
 options.SetOutputModelGetInitializerLocationFunc(capture,nullptr);
 Ort::ThrowOnError(Ort::CompileModel(env,options));
}
