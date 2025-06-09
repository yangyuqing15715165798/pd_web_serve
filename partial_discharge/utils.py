def transform_routes_data(data):
    transformed_data = []
    for item in data:
        transformed_item = {
            "path": item["path"],
            "component": item["component"],
            "children": [
                {
                    "path": item["children_path"],
                    "component": item["children_component"],
                    "name": item["children_name"],
                    "meta": {
                        "title": item["children_meta_title"],
                        "icon": item["children_meta_icon"],
                    },
                }
            ],
        }
        transformed_data.append(transformed_item)
    return transformed_data


def res_form(code=20000, data=None, message="success"):
    return {"code": code, "data": data, "message": message}
