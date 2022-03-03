import bs4
import urllib.request as lib
import string
import math
import pymysql
import re
import json
from urllib import parse


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


# 爬蟲程式
def getDate(url, products_data):

    # 由於此網頁為XHR(Ajax)動態生成, 因此必須去抓WEB API的data而非網頁原始碼
    def getPageXHR(pageId, pageNum, mode):

        # 設定post method所傳的參數(取哪個分類的第幾頁)
        data = {
            "categoryId": pageId,
            "orderBy": 21,
            "pageIndex": pageNum,
            "pageSize": 20,
            "isLoadThree": False
        }

        data = parse.urlencode(data).encode()
        request = lib.Request(
            "https://online.carrefour.com.tw/ProductShowcase/Catalog/CategoryJson", 
            data=data,
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
                "Cookie": "Carrefour.WebDefault_Address_mobile=true"
            },
            origin_req_host="https://online.carrefour.com.tw"
        )

        with lib.urlopen(request) as response:
            result = json.load(response)

        result = result["content"]

        # mode = 0 時代表要取該分類的頁數, 1的時候代表要取該分類在該頁的所有商品資訊
        if not mode:
            products_count = int(result["Count"])
            page_num = products_count // 20 + 1 if products_count % 20 != 0 else products_count // 20
            return page_num
        else:
            return result["ProductListModel"]


    # 取得商品API時必須post的data也要由另一支API取得
    def getPageId(target):

        # 在取PageXHR的時候需要該分類的Id, 而該Id也是動態生成, 故需要在抓另一個WEB API以取得
        data = {
            "langId": 1,
            "langCode": "zh-TW"
        }

        data = parse.urlencode(data).encode()
        request = lib.Request(
            "https://online.carrefour.com.tw/ProductShowcase/Catalog/GetMenuJson", 
            data=data, 
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
                "Cookie": "Carrefour.WebDefault_Address_mobile=true"
            },
            origin_req_host="https://online.carrefour.com.tw"
        )

        with lib.urlopen(request) as response:
            results = json.load(response)

        results = results["content"]

        for result in results:
            result = result["SubCategories"]

            for sub_result in result:
                if sub_result["Name"] == target:
                    return int(sub_result["Id"])


    def getPageData(category, subcategory, page_id, page_num, products_data):
        data = getPageXHR(page_id, page_num, 1)

        # 取得每個商品所需的資訊
        for info in data:
            print(info["Name"], int(info["RealPrice"]), info["Specification"], sep=",")
            products_data[category].append([info["Name"], int(info["RealPrice"]), info["Specification"]])
        

    request = lib.Request(url, headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
    })

    with lib.urlopen(request) as response:
        data = response.read().decode("utf-8")

    root = bs4.BeautifulSoup(data, "html.parser")
    left_side = root.find("div", class_="detailed-class")
    categories = left_side.find_all("li")

    for i in range(len(categories)):
        all_href = []
        all_subcategory = []
        rows = categories[i].find_all("div", class_="top1 left-item")  # 先取得所有大分類

        for row in rows:
            all_href.append(url + row.find("a", href=True)["href"])
            all_subcategory.append(row.find("a", href=True).text.strip())  # 在取得大分類中的所有子分類

        categories[i] = [categories[i].text.strip().split("\n")[0], all_subcategory]

    for category in categories:

        products_data[category[0]] = []  # 在儲存資料的dict中初始化該大分類的value為一個空list

        for i in range(len(category[1])):
            page_id = getPageId(category[1][i])
            page_count = getPageXHR(page_id, 1, 0)
            
            for j in range(page_count):
                getPageData(category[0], category[1][i], page_id, j+1, products_data)


# 刪除字串中所有空格
def trim(string):
    return string.replace(" ", "")


# 資料存入資料庫
def insert_into_db(data):
    db_settings = get_db_settings()

    con = pymysql.connect(**db_settings)

    with con.cursor() as cursor:
        delCom = "delete from products_info where market = 'Carrefour'"  # 先將原本的資料全數刪除再輸入新的資料
        com = "insert into products_info (product_name, product_price, category, market, cp_val, status, detail) values(%s, %s, %s, %s, %s, %s, %s)"

        # cursor.execute(delCom)
        # con.commit()

        for product_data in data.items():
            print(product_data[0])

            for info in product_data[1]:
                print(info[0], info[1], info[2], sep=",")
                # cursor.execute(com, (trim(info[0]), info[1], trim(product_data[0]), "Carrefour", 0, 1, trim(info[2])))
                # con.commit()

    con.close()


# 算出所有商品的CP值
def count_all_cp():

    # 下面先從資料庫中取出所有家樂福的商品資料
    db_settings = get_db_settings()

    con = pymysql.connect(**db_settings)
    skip_categories = ["3C", "大小家電", "傢俱寢飾"]

    with con.cursor() as cursor:
        select = "select * from products_info where market = 'Carrefour'"
        update = "update products_info set cp_val = %s, cp_val_unit = %s where market = 'Carrefour' and product_name = %s and detail = %s and product_price = %s"
        update_without_unit = "update products_info set cp_val = %s, cp_val_unit = %s where market = 'Carrefour' and product_name = %s and detail = %s and product_price = %s"

        cursor.execute(select)
        result = cursor.fetchall()
        
        for info in result:
            if info[2].strip() not in skip_categories:
                cp_val = countCP(list(info))

                # if len(cp_val) == 1:
                #     cursor.execute(
                #         update_without_unit,
                #         (cp_val[0], "",info[0], info[6], info[1])
                #     )
                #     con.commit()
                # else:
                #     cursor.execute(
                #         update,
                #         (cp_val[1], cp_val[0], info[0], info[6], info[1])
                #     )
                #     con.commit()

        print(len(result))


# 家樂福的單位會包含英文加中文, 故刪除英文以幫助判斷 ex. Can罐 --> 罐
def delete_all(s):
    
    unit_to_delete = ["PC", "Pack", "Bag", "Can", "CAN", "Bottle", "BOTTLE", "Pair", "Cup","Box", "Set", "Card", "Bowl", "Bucket"]

    for i in range(len(unit_to_delete)):
        if unit_to_delete[i] in s:
            s = s.replace(unit_to_delete[i], "")

    return s


def findKeywords(target):

    # 先看有沒有乘的符號且符號後面接的是數字, 有就分割字串(需判斷有無數字否則會出錯 ex. XO醬)
    if re.search(r"\*+\d+", target[0]):
        target[0] = target[0].split("*")
    elif re.search(r"x+\d+", target[0]):
        target[0] = target[0].split("x")
    elif re.search(r"X+\d+", target[0]):
        target[0] = target[0].split("X")
    else:
        # 最後無論如何都把target[0]轉成list, 因為下面都是將target[0]作為list做操作
        target[0] = [target[0]]

    status = False  # 代表該商品是否有詳細的規格(代表是否可以計算出cp值)

    # 要查找的單位量詞
    unit_condition = r"(罐|盒|抽|包|瓶|袋|入|錠|粒|杯|塊|顆|片|條|尾|件|雙|組|台|本|卡|支|個|碗|桶|捲|KG|kg|G|g|L|ML|ml|c\.c|cc|oz|公斤|克|公克|公升|毫升)"  # 後續正則式需用到的單位關鍵字

    result = [0]
    search_target_val = target[0][0]  # 等等尋找單位量詞的目標字串

    # 利用正則式找尋是否有 浮點數或整數 + 單位量詞在字串內
    number = re.search(
        r"(\+*\d+\.+\d+{}+)|(\+*\d+{}+)".format(unit_condition, unit_condition),
            search_target_val
        )

    # 若有找到數字+量詞則將字串進行分割並反覆尋找直到找不到為止
    # 利用result儲存找到的結果
    while number:

        status = True
        result.pop(-1)
        number = number.span()
        units = search_target_val[number[0]:number[1]]
        units_number = re.search(r"\+*\d+\.*\d*", units).span()

        result.extend([
            search_target_val[:number[0]],
            search_target_val[number[0]:number[0]+units_number[1]], 
            search_target_val[number[0]+units_number[1]:number[1]],
            search_target_val[number[1]:]
        ])

        search_target_val = search_target_val[number[1]:]  # 將要查找的字串更新為找到的量詞後的字串(再往後找有沒有量詞)

        number = re.search(
            r"(\+*\d+\.+\d+{}+)|(\+*\d+{}+)".format(unit_condition, unit_condition),
            search_target_val
        )

    value = 0

    if status:
        value = 1
        
        for i in range(1, len(result) - 1):

            if result[i] == "+-":
                value /= float(result[i+1])
                continue

            if re.match(r"\+*[0-9]+\.*[0-9]*", result[i]):

                # 此為因應有些產品會有包含運算的數量ex:3+1包, 因此必須作特殊的處裡
                if re.match(r"\+", result[i]):
                    for j in range(i - 1, 0, -1):
                        if re.match(r"[0-9]+\.*[0-9]*", result[j]):
                            value /= float(result[j])
                            value *= float(result[i]) + float(result[j])
                            break
                else:
                    value *= float(result[i])
        
        # 除了分析result中的結果之外, 還需分析最一開始用乘法符號作分割的結果
        if len(target[0]) > 1:
            
            number = re.match(r"[0-9]+\.*[0-9]*({}+|\b)".format(unit_condition), target[0][1])
            number = number.span() if number != None else None

            if number:
                number = re.match(r"[0-9]+\.*[0-9]*", target[0][1]).span()
                value *= float(target[0][1][number[0]:number[1]])

        return (status, value, result[2])

    # 有時候雖然沒有找到相關的單位量詞, 但也需分析最一開始用乘法符號作分割的結果
    if len(target[0]) > 1:
        value = 1
        number = re.match(r"[0-9]+\.*[0-9]*{}+".format(unit_condition), target[0][1])
        number = number.span() if number != None else None

        if number:
            number = re.match(r"[0-9]+\.*[0-9]*", target[0][1]).span()
            value *= float(target[0][1][number[0]:number[1]])
            status = True  # 若乘法符號後有相關單位就將status改為True
            return (status, value, target[0][1][number[1]:])

    return (status, value, 0)


def countCP(product):

    product[0] = trim(product[0])
    product[6] = trim(product[6])
    product[6] = delete_all(product[6])
    product_name = re.split(r"/+(罐|盒|抽|包|瓶|袋|入|錠|粒|杯|塊|顆|片|條|尾|組|台|本|卡|支|個|碗|桶|捲|KG|kg|G|g|L|ML|ml|c\.c|cc|oz|公斤|克|公克|公升|毫升)", product[0], 1)
    product_detail = re.split(r"/+(罐|盒|抽|包|瓶|袋|入|錠|粒|杯|塊|顆|片|條|尾|組|台|本|卡|支|個|碗|桶|捲|KG|kg|G|g|L|ML|ml|c\.c|cc|oz|公斤|克|公克|公升|毫升)", product[6], 1)

    result = [False, 0, 0]
    result_name = findKeywords(product_name)
    result_detail = findKeywords(product_detail)

    # 之所以要分別用name和detail去判斷cp值是因為有時候兩者給的規格不相同
    # 下面的判斷最終的result應採取name的還是detail的
    # 而判斷依據為: 先選擇有算出cp值的(及findKeywords return的第一個值為true)
    # 若兩個判斷出來都有cp值就選value大的(由於在這個階段只會算出商品有多少單位, 故越多單位代表資訊越詳細)
    # ex. 500ml*24罐(12000單位) vs. 24罐(24單位)
    if result_name[0] and result_detail[0]:
        result = result_detail if result_detail[1] > result_name[1] else result_name
    else:
        if result_detail[0]:
            result = result_detail

        if result_name[0]:
            result = result_name

    if not result[0]:
        print("NoCp:", product[1])
        return [product[1]]
    else:
        print("每{} {}元".format(result[2], format(float(product[1]) / result[1], ".2f")))
        return [result[2], format(float(product[1]) / result[1], ".2f")]


# url = "https://online.carrefour.com.tw"
# products_data = {}
# getDate(url, products_data)
# insert_into_db(products_data)
count_all_cp()