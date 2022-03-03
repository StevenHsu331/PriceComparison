from django.shortcuts import render
from django.http import HttpResponse
import pymysql
import json


# 避免將資料庫資訊暴露在程式碼中, 另外儲存在讀取
def get_db_settings():
    with open("dbsetting.txt") as setting:
        db_settings = {}
        result = setting.read()
        result = result.replace("\n", "")
        result = result.split(",")

        for i in range(len(result)):
            result[i] = result[i].split(":")
            if i == 1:
                db_settings[result[i][0]] = int(result[i][1])
            else:
                db_settings[result[i][0]] = result[i][1]

        return db_settings


# 回傳首頁html檔
def Home(request):
    return render(request, "Home.html", locals())


# 接受ajax的data並在資料庫中做查詢
def getResult(request):
    method = request.POST["method"]
    amount = request.POST["amount"]
    order = request.POST["order"]
    product = request.POST["key"]
    result = [[],[]]

    # 由於資料庫中cp值代表每單位的價格, 所以值越低越好, 若使用者選取'高到低'做排序, 反而要找'低到高'才符合高cp值的概念
    if method == "cp_val":
        order = "asc" if order == "desc" else "desc"

    db_settings = get_db_settings()

    con = pymysql.connect(**db_settings)

    # 執行資料庫查詢語法
    with con.cursor() as cursor:
        if amount != "0":
            # 若不加'%'的話所查詢的關鍵字中間不能有其他字ex. key=林鳳營鮮乳 會查不到林鳳營高品質鮮乳
            product = "%".join(product)

            com = "select * from products_info where product_name like %s and status = 1 order by %s %s limit %s;"
            com = com %("'%" + product + "%'", method, order, amount)

            cursor.execute(com)

            result = cursor.fetchall()
        else:
            product = product.split(",")
        
            for i in range(len(product)):
                product[i] = "%".join(product[i])
                com1 = "select * from products_info where product_name like %s and status = 1 and market = 'rt-market' order by %s %s limit 1;"
                com2 = "select * from products_info where product_name like %s and status = 1 and market = 'carrefour' order by %s %s limit 1;"
                
                com1 = com1 %("'%" + product[i] + "%'", method, order)
                com2 = com2 %("'%" + product[i] + "%'", method, order)

                cursor.execute(com1)
                data = cursor.fetchall()
                result[0].append([data[0][0], data[0][1], data[0][4]])

                cursor.execute(com2)
                data = cursor.fetchall()
                result[1].append([data[0][0], data[0][1], data[0][4]])

    con.close()

    # 將結果轉為Json格式以方便前端使用
    result = json.dumps(result, ensure_ascii=False).encode("utf-8")
    return HttpResponse(result.decode())