#coding=gbk
#代码注入是指程序员错误的认为用户提供的指令仅会执行无害的操作，而没有对其进行验证。
from django.http import HttpResponse
def pyeval(request):
    op = request.GET['operation']
    result = eval(op)

