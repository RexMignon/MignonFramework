function isArray(obj) {
    try {
        return Array.isArray(obj);
    } catch (e) {
        return ![]
    }
}

function getCurrentTime() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    return ` \n~~**$+=> ${year}年${month}月${day}日 ${hours}:${minutes}:${seconds}.${milliseconds}`;
}

function JSONparse(jsonStr, num) {
    if (!isArray(jsonStr)) {
        console.log(`\n参数 ${num}  初步数组检测成功  =>`)
        if (typeof (jsonStr) === "string" && !![]) {
            console.log(`\n[ 参数 ${num} <= 检测到字符串输入，正在尝试转json格式....  ]`)
            try {
                jsonStr = JSON.parse(jsonStr)
                if (!isArray(jsonStr)) {
                    console.log("\n[  转JSON格式成功<<==  ]")
                    return jsonStr
                } else {
                    console.log("\n  检测到JSON.parse后为数组，重新键入 <=  ")
                    return ![]
                }

            } catch (e) {
                console.log("")
                console.info("\n" + "[ 参数" + num + " JSON.parse()方法转json格式失败=>  JSON格式不标准或非JSON格式  ]")
                console.log("")
                const match = e.toString().match(/at position (\d+)/)
                console.log("\n 参数" + num + "  错误信息=>  [ ", e.toString().replace("SyntaxError:", ""), "   ]  \n")
                if (match) {
                    const position = match[1]
                    for (var y = 0; y < jsonStr.length; y++) {
                        if (y === parseInt(position)) {
                            var stir = "\n[    " + jsonStr[y - 6] + jsonStr[y - 5] + jsonStr[y - 4] + jsonStr[y - 3] + jsonStr[y - 2] + jsonStr[y - 1] + jsonStr[y] + `   ] <=  Error at ${position} (箭头所指出错字符)`
                            stir = stir.replaceAll("undefined", "")
                            console.info("\n通过正则表达式匹配到的错误位置=>: " + position + "\n" + stir + "\n")
                            break
                        }
                    }
                }
                return ![]
            }
        } else {
            console.warn(`\n[ 参数 ${num.toString()}  TypeOf函数JSON验证通过 (WARNING) ]`)
            return jsonStr
        }
    } else {
        console.log("\n参数 " + num + "  为Array,重新键入   <=\n")
        return ![]
    }
}

var jsondec = (oba, obb) => {
    let list = Array()
    var timestamp = getCurrentTime()
    list.push("\n------------START--------------\n      TIME =>" + timestamp + "\n------------START-END----------\n")
    oba = JSONparse(oba, 1)
    if (oba) {
        obb = JSONparse(obb, 2)
    } else {
        obb = ![]
    }
    var h = ""
    var w = ""
    var g = ""
    var e = ""
    for (let i = 0; i <= 27; i++) {
        h += "="
        w += "//"
        g += "*"
        e += "^"
    }
    if (oba && obb) {
        list.push(`\n${h}\n=>>       [MIGNON]       <<= \n${h}`)
        const sortedKeys1 = Object.keys(oba).sort();
        const sortedKeys2 = Object.keys(obb).sort();

        const sortedJson1 = {};
        const sortedJson2 = {};

        for (const key of sortedKeys1) {
            sortedJson1[key] = oba[key];
        }

        for (const key of sortedKeys2) {
            sortedJson2[key] = obb[key];
        }
        if (JSON.stringify(sortedJson1) === JSON.stringify(sortedJson2) && !![]) {
            list.push(`\n${e}\n   =>  两JSON相同  <=\n${e}\n`)
        } else {
            let a = Object.keys(oba)
            let b = Object.keys(obb)
            if (a.length !== 0 && b.length !== 0) {
                list.push(`\n${e}\n      两JSON不同=>\n${e}\n`)
                !function () {
                    for (var akeys of a) {
                        if (b.includes(akeys)) {
                            var f = (oba, obb, akeys) => {
                                list.push(`\n${h}\n=>> < ${akeys} >不相等 <<= `)
                                let hr = oba[akeys].length >= obb[akeys].length ? oba[akeys] : obb[akeys]
                                if (oba[akeys].length !== obb[akeys].length && !![]) {
                                    list.push("      长度不同   <=")
                                } else {
                                    for (var i = 0; i <= hr.length; i++) {
                                        if (oba[akeys].charAt(i) !== obb[akeys].charAt(i)) {
                                            for (var s = 1; s <= hr.length - i; s++) {
                                                if (oba[akeys].charAt(i + s) !== obb[akeys].charAt(i + s)) {
                                                    void 0
                                                } else {
                                                    if (i + 1 === i + s&&!![]) {
                                                        list.push(`第^=>>  ( ${i + 1} )  位  ^不同   <<==\n参数1=> \n`)
                                                    } else {
                                                        list.push(`第^=>>  ( ${i + 1} - ${i + s} )  位  ^不同   <<==\n参数1=> \n`)
                                                    }
                                                    let wd = []
                                                    if (i - 7 >= 0) {
                                                        var gcc = i - 7
                                                        var cpp = 0
                                                    } else {
                                                        gcc = 0
                                                        cpp = 7 - i
                                                    }
                                                    if (i + s - 1 === oba[akeys].length) {
                                                        cpp = 0
                                                    }
                                                    for (var wc = gcc; wc < i + s - 1 + 7 + cpp; wc++) {
                                                        if (i === wc) {
                                                            wd.push("  (  ")
                                                        } else if (wc === i + s) {
                                                            wd.push("  )  ")
                                                        }
                                                        wd.push(`${obb[akeys].charAt(wc)}`)
                                                    }
                                                    var wq = "即=>  [  "
                                                    for (var wa = 0; wa < wd.length; wa++) {
                                                        wq += wd[wa]
                                                    }
                                                    wq += "  ]"
                                                    list.push(wq)
                                                    list.push(`参数2=>>\n`)
                                                    let d = []
                                                    for (var c = gcc; c < i + s - 1 + 7 + cpp; c++) {
                                                        if (i === c) {
                                                            d.push("  (  ")
                                                        } else if (c === i + s) {
                                                            d.push("  )  ")
                                                        }
                                                        d.push(`${oba[akeys].charAt(c)}`)
                                                    }
                                                    var q = "即=>  [  "
                                                    for (var a = 0; a < d.length; a++) {
                                                        q += d[a]
                                                    }
                                                    q += "  ]"
                                                    list.push(q)
                                                    break
                                                }
                                            }
                                            i += s
                                        }
                                    }
                                }
                                list.push(`${h}\n\n\n`)
                            }
                            oba[akeys] = typeof (oba[akeys]) !== "string" && typeof (oba[akeys]) !== void 0 ? JSON.stringify(oba[akeys]) : oba[akeys]
                            obb[akeys] = typeof (obb[akeys]) !== "string" && typeof (oba[akeys]) !== void 0 ? JSON.stringify(obb[akeys]) : obb[akeys]
                            oba[`${akeys}`] === obb[`${akeys}`] && !![] ? void 0 : f(oba, obb, akeys)
                        }
                        b.includes(akeys) && !![] ? void 0 : list.push(`\n\n${w}\n   参数1的 =>  <  ${akeys} >   <=无与参数2相同的key\n${w}`)
                    }
                    for (var bkeys of b) {
                        a.includes(bkeys) && !![] ? void 0 : list.push(`\n\n${w}\n   参数2的 =>  <  ${bkeys} >   <=无与参数1相同的key\n${w}`)
                    }
                }()
            } else {
                list.push("\n----请检查格式是否正确，未检测到KEY----")
            }
        }
    }
    list.push("\n------------END--------------\n (timestamp与起始相同用来定位) TIME =>" + timestamp + "\n------------END-END----------\n\n");
    return list
}
module.exports = {
    jsondec: jsondec
}